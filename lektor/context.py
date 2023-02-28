from contextlib import contextmanager

from jinja2 import Undefined
from werkzeug.local import LocalProxy
from werkzeug.local import LocalStack

from lektor.reporter import reporter


_ctx_stack = LocalStack()


def url_to(*args, **kwargs):
    """Calculates a URL to another record."""
    ctx = get_ctx()
    if ctx is None:
        raise RuntimeError("No context found")
    return ctx.url_to(*args, **kwargs)


def get_asset_url(asset):
    """Calculates the asset URL relative to the current record."""
    ctx = get_ctx()
    if ctx is None:
        raise RuntimeError("No context found")
    asset = ctx.pad.get_asset(asset)
    if asset is None:
        return Undefined("Asset not found")
    return ctx.get_asset_url(asset)


@LocalProxy
def site_proxy():
    """Returns the current pad."""
    ctx = get_ctx()
    if ctx is None:
        return Undefined(hint="Cannot access the site from here", name="site")
    return ctx.pad


@LocalProxy
def config_proxy():
    """Returns the current config."""
    return site_proxy.db.config


def get_ctx():
    """Returns the current context."""
    return _ctx_stack.top


def get_locale(default="en_US"):
    """Returns the current locale."""
    ctx = get_ctx()
    if ctx is not None:
        rv = ctx.locale
        if rv is not None:
            return rv
        return ctx.pad.db.config.site_locale
    return default


class Context:
    """The context is a thread local object that provides the system with
    general information about in which state it is.  The context is created
    whenever a source is processed and can be accessed by template engine and
    other things.

    It's considered read and write and also accumulates changes that happen
    during processing of the object.
    """

    def __init__(self, artifact=None, pad=None):
        if pad is None:
            if artifact is None:
                raise TypeError(
                    "Either artifact or pad is needed to construct a context."
                )
            pad = artifact.build_state.pad

        if artifact is not None:
            self.artifact = artifact
            self.source = artifact.source_obj
            self.build_state = self.artifact.build_state
        else:
            self.artifact = None
            self.source = None
            self.build_state = None

        self.exc_info = None

        self.pad = pad

        # Processing information
        self.referenced_dependencies = set()
        self.referenced_virtual_dependencies = set()
        self._tracked_sources = set()
        self.sub_artifacts = []

        self.flow_block_render_stack = []

        self._forced_base_url = None
        self._resolving_url = False

        # General cache system where other things can put their temporary
        # stuff in.
        self.cache = {}

        self._dependency_collectors = []

    @property
    def env(self):
        """The environment of the context."""
        return self.pad.db.env

    @property
    def record(self):
        """If the source is a record it will be available here."""
        rv = self.source
        if rv is not None and rv.source_classification == "record":
            return rv
        return None

    @property
    def locale(self):
        """Returns the current locale if it's available, otherwise `None`.
        This does not fall back to the site locale.
        """
        source = self.source
        if source is not None:
            alt_cfg = self.pad.db.config["ALTERNATIVES"].get(source.alt)
            if alt_cfg:
                return alt_cfg["locale"]
        return None

    def push(self):
        _ctx_stack.push(self)

    @staticmethod
    def pop():
        _ctx_stack.pop()

    def __enter__(self):
        self.push()
        return self

    def __exit__(self, exc_type, exc_value, tb):
        self.pop()

    @property
    def base_url(self):
        """The URL path for the current context."""
        if self._forced_base_url:
            return self._forced_base_url
        if self.source is not None:
            return self.source.url_path
        return "/"

    def url_to(
        self,
        path,
        alt=None,
        absolute=None,
        external=None,
        resolve=None,
        strict_resolve=None,
    ):
        """Returns a URL to another path."""
        if self.source is None:
            raise RuntimeError(
                "Can only generate paths to other pages if "
                "the context has a source document set."
            )
        return self.source.url_to(
            path,
            alt=alt,
            base_url=self.base_url,
            absolute=absolute,
            external=external,
            resolve=resolve,
            strict_resolve=strict_resolve,
        )

    def get_asset_url(self, asset):
        """Calculates the asset URL relative to the current record."""
        if self.source is None:
            raise RuntimeError(
                "Can only generate paths to assets if "
                "the context has a source document set."
            )
        asset_url = self.source.url_to("!" + asset.url_path)
        info = self.build_state.get_file_info(asset.source_filename)
        self.record_dependency(asset.source_filename)
        return f"{asset_url}?h={info.checksum[:8]}"

    def sub_artifact(self, *args, **kwargs):
        """Decorator version of :func:`add_sub_artifact`."""

        def decorator(f):
            self.add_sub_artifact(build_func=f, *args, **kwargs)
            return f

        return decorator

    def add_sub_artifact(
        self,
        artifact_name,
        build_func=None,
        sources=None,
        source_obj=None,
        config_hash=None,
    ):
        """Sometimes it can happen that while building an artifact another
        artifact needs building.  This function is generally used to record
        this request.
        """
        if self.build_state is None:
            raise TypeError(
                "The context does not have a build state which "
                "means that artifact declaration is not possible."
            )
        aft = self.build_state.new_artifact(
            artifact_name=artifact_name,
            sources=sources,
            source_obj=source_obj,
            config_hash=config_hash,
        )
        self.sub_artifacts.append((aft, build_func))
        reporter.report_sub_artifact(aft)

    def record_dependency(self, filename, affects_url=None):
        """Records a dependency from processing.

        If ``affects_url`` is set to ``False`` the dependency will be ignored if
        we are in the process of resolving a URL.
        """
        if self._resolving_url and affects_url is False:
            return
        self.referenced_dependencies.add(filename)
        for coll in self._dependency_collectors:
            coll(filename)

    def record_virtual_dependency(self, virtual_source):
        """Records a dependency from processing."""
        self.referenced_virtual_dependencies.add(virtual_source)
        for coll in self._dependency_collectors:
            coll(virtual_source)

    def track_source_dependency(self, source):
        """Track all dependencies of source object"""
        if source not in self._tracked_sources:
            self._tracked_sources.add(source)
            for filename in source.iter_source_filenames():
                self.record_dependency(filename)
            for virtual_source in source.iter_virtual_sources():
                self.record_virtual_dependency(virtual_source)

            if hasattr(source, "datamodel"):
                db = source.pad.db
                for model in db.iter_dependent_models(source.datamodel):
                    if model.filename:
                        self.record_dependency(model.filename)
                # XXX: In the case that the record's datamodel is
                # implied, then the datamodel depends on the
                # datamodel(s) of our parent(s).  We do not currently
                # record that.

    @contextmanager
    def gather_dependencies(self, func):
        """For the duration of the `with` block the provided function will be
        invoked for all dependencies encountered.
        """
        self._dependency_collectors.append(func)
        try:
            yield
        finally:
            self._dependency_collectors.pop()

    @contextmanager
    def changed_base_url(self, value):
        """Temporarily overrides the URL path of the context."""
        old = self._forced_base_url
        self._forced_base_url = value
        try:
            yield
        finally:
            self._forced_base_url = old


@contextmanager
def ignore_url_unaffecting_dependencies(value=True):
    """Ignore dependencies which do not affect URL resolution within context."""
    ctx = get_ctx()
    if ctx is not None:
        old = ctx._resolving_url
        ctx._resolving_url = value
    try:
        yield
    finally:
        if ctx is not None:
            ctx._resolving_url = old
