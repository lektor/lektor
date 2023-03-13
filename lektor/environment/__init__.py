import fnmatch
import os
import uuid
from functools import update_wrapper

import babel.dates
import jinja2
from jinja2.loaders import split_template_path

from lektor.constants import PRIMARY_ALT
from lektor.context import config_proxy
from lektor.context import get_asset_url
from lektor.context import get_ctx
from lektor.context import get_locale
from lektor.context import site_proxy
from lektor.context import url_to
from lektor.environment.config import Config
from lektor.environment.config import DEFAULT_CONFIG  # noqa - reexport
from lektor.environment.config import ServerInfo  # noqa - reexport
from lektor.environment.config import update_config_from_ini  # noqa - reexport
from lektor.environment.expressions import Expression  # noqa - reexport
from lektor.environment.expressions import FormatExpression  # noqa - reexport
from lektor.markdown import Markdown
from lektor.packages import load_packages
from lektor.pluginsystem import initialize_plugins
from lektor.pluginsystem import PluginController
from lektor.publisher import builtin_publishers
from lektor.utils import format_lat_long
from lektor.utils import tojson_filter


def _prevent_inlining(wrapped):
    """Ensure wrapped jinja filter does not get inlined by the template compiler.

    The jinja compiler normally assumes that filters are pure functions (whose
    result depends only on their parameters) and will inline filter calls that
    are applied to compile-time constants.

    E.g.

        'say {{ "foo" | upper }}'

    will be compiled to

        "say Foo"

    Many of our filters depend on global state (e..g the Lektor build context).

    Applying this decorator to them will ensure they are not inlined.
    """
    # the use of @pass_context will prevent inlining
    @jinja2.pass_context
    def wrapper(_jinja_ctx, *args, **kwargs):
        return wrapped(*args, **kwargs)

    return update_wrapper(wrapper, wrapped)


def _dates_filter(name, wrapped):
    """Wrap one of the babel.dates.format_* functions for use as a jinja filter.

    This will create a jinja filter that will:

    - Check for *undefined* date/time input (and, in that case, return an empty string).

    - Check that the ``format`` and ``locale`` parameters, if provided, have the correct
      types, otherwise raising ``TypeError``.

    - Raise ``TypeError`` with a somewhat informative message if the wrapped formatting
      function raises an unexpected exception.  Such an exception is most likely due to
      being passed an unsupported date/time time.  (The Babel formatting functions
      accept a fairly wide range of input types — and that range might potentially vary
      between releases — so we do not explicitly check the input type before passing it
      on to Babel.)

    If `locale` is not specified, we fill it in based on the current *alt*.

    """

    @_prevent_inlining
    def wrapper(arg, format="medium", **kwargs):
        if isinstance(arg, jinja2.Undefined):
            # This will typically return an empty string, though it depends on the
            # specific type of undefined instance.  E.g. if arg is a DebugUndefined, it
            # will return a more descriptive message, and if arg is a StrictUndefined,
            # an UndefinedError will be raised.
            return str(arg)

        if not isinstance(format, str):
            raise TypeError(
                f"The 'format' parameter to '{name}' should be a str, not {format!r}"
            )

        locale = kwargs.get("locale")
        if locale is None:
            kwargs["locale"] = get_locale("en_US")

        try:
            return wrapped(arg, format, **kwargs)
        except (TypeError, ValueError):
            raise
        except Exception as exc:
            raise TypeError(
                f"While evaluating filter '{name}', an unexpected exception was raised. "
                "This is likely caused by an input or parameter of an unsupported type."
            ) from exc

    return update_wrapper(wrapper, wrapped)


# Special files that should always be ignored.
IGNORED_FILES = ["thumbs.db", "desktop.ini", "Icon\r"]

# These files are important for artifacts and must not be ignored when
# they are built even though they start with dots.
SPECIAL_ARTIFACTS = [".htaccess", ".htpasswd"]

# Default glob pattern of ignored files.
EXCLUDED_ASSETS = ["_*", ".*"]

# Default glob pattern of included files (higher-priority than EXCLUDED_ASSETS).
INCLUDED_ASSETS = []


def any_fnmatch(filename, patterns):
    for pat in patterns:
        if fnmatch.fnmatch(filename, pat):
            return True

    return False


class CustomJinjaEnvironment(jinja2.Environment):
    def _load_template(self, name, globals):
        ctx = get_ctx()

        try:
            rv = jinja2.Environment._load_template(self, name, globals)
            if ctx is not None:
                filename = rv.filename
                ctx.record_dependency(filename)
            return rv
        except jinja2.TemplateSyntaxError as e:
            if ctx is not None:
                ctx.record_dependency(e.filename)
            raise
        except jinja2.TemplateNotFound as e:
            if ctx is not None:
                # If we can't find the template we want to record at what
                # possible locations the template could exist.  This will help
                # out watcher to pick up templates that will appear in the
                # future.  This assumes the loader is a file system loader.
                for template_name in e.templates:
                    pieces = split_template_path(template_name)
                    for base in self.loader.searchpath:
                        ctx.record_dependency(os.path.join(base, *pieces))
            raise


def lookup_from_bag(*args):
    pieces = ".".join(x for x in args if x)
    return site_proxy.databags.lookup(pieces)


class Environment:
    def __init__(self, project, load_plugins=True, extra_flags=None):
        self.project = project
        self.root_path = os.path.abspath(project.tree)

        self.theme_paths = [
            os.path.join(self.root_path, "themes", theme)
            for theme in self.project.themes
        ]

        if not self.theme_paths:
            # load the directories in the themes directory as the themes
            try:
                for fname in os.listdir(os.path.join(self.root_path, "themes")):
                    f = os.path.join(self.root_path, "themes", fname)
                    if os.path.isdir(f):
                        self.theme_paths.append(f)
            except OSError:
                pass

        template_paths = [
            os.path.join(path, "templates")
            for path in [self.root_path] + self.theme_paths
        ]

        self.jinja_env = CustomJinjaEnvironment(
            autoescape=self.select_jinja_autoescape,
            extensions=["jinja2.ext.do"],
            loader=jinja2.FileSystemLoader(template_paths),
        )

        from lektor.db import F, get_alts  # pylint: disable=import-outside-toplevel

        self.jinja_env.filters.update(
            tojson=tojson_filter,
            latformat=lambda x, secs=True: format_lat_long(lat=x, secs=secs),
            longformat=lambda x, secs=True: format_lat_long(long=x, secs=secs),
            latlongformat=lambda x, secs=True: format_lat_long(secs=secs, *x),
            url=_prevent_inlining(url_to),
            asseturl=_prevent_inlining(get_asset_url),
            markdown=_prevent_inlining(Markdown),
        )
        self.jinja_env.globals.update(
            F=F,
            url_to=url_to,
            site=site_proxy,
            config=config_proxy,
            bag=lookup_from_bag,
            get_alts=get_alts,
            get_random_id=lambda: uuid.uuid4().hex,
        )
        self.jinja_env.filters.update(
            dateformat=_dates_filter("dateformat", babel.dates.format_date),
            datetimeformat=_dates_filter("datetimeformat", babel.dates.format_datetime),
            timeformat=_dates_filter("timeformat", babel.dates.format_time),
        )

        # pylint: disable=import-outside-toplevel
        from lektor.types import builtin_types

        self.types = builtin_types.copy()

        self.publishers = builtin_publishers.copy()

        # The plugins that are loaded for this environment.  This is
        # modified by the plugin controller and registry methods on the
        # environment.
        self.plugin_controller = PluginController(self, extra_flags)
        self.plugins = {}
        self.plugin_ids_by_class = {}
        self.build_programs = []
        self.special_file_assets = {}
        self.special_file_suffixes = {}
        self.custom_url_resolvers = []
        self.custom_generators = []
        self.virtual_sources = {}

        if load_plugins:
            self.load_plugins()
        # pylint: disable=import-outside-toplevel
        from lektor.db import siblings_resolver

        self.virtualpathresolver("siblings")(siblings_resolver)

    @property
    def asset_path(self):
        return os.path.join(self.root_path, "assets")

    @property
    def temp_path(self):
        return os.path.join(self.root_path, "temp")

    def load_plugins(self):
        """Loads the plugins."""
        load_packages(self)
        initialize_plugins(self)

    def load_config(self):
        """Loads the current config."""
        return Config(self.project.project_file)

    def new_pad(self):
        """Convenience function to create a database and pad."""
        from lektor.db import Database  # pylint: disable=import-outside-toplevel

        return Database(self).new_pad()

    def is_uninteresting_source_name(self, filename):
        """These files are ignored when sources are built into artifacts."""
        fn = filename.lower()
        if fn in SPECIAL_ARTIFACTS:
            return False

        proj = self.project
        if any_fnmatch(filename, INCLUDED_ASSETS + proj.included_assets):
            # Included by the user's project config, thus not uninteresting.
            return False
        return any_fnmatch(filename, EXCLUDED_ASSETS + proj.excluded_assets)

    @staticmethod
    def is_ignored_artifact(asset_name):
        """This is used by the prune tool to figure out which files in the
        artifact folder should be ignored.
        """
        fn = asset_name.lower()
        if fn in SPECIAL_ARTIFACTS:
            return False
        return fn[:1] == "." or fn in IGNORED_FILES

    def render_template(self, name, pad=None, this=None, values=None, alt=None):
        ctx = self.make_default_tmpl_values(pad, this, values, alt, template=name)
        return self.jinja_env.get_or_select_template(name).render(ctx)

    def make_default_tmpl_values(
        self, pad=None, this=None, values=None, alt=None, template=None
    ):
        values = dict(values or ())

        # If not provided, pick the alt from the provided "this" object.
        # As there is no mandatory format for it, we make sure that we can
        # deal with a bad attribute there.
        if alt is None:
            if this is not None:
                alt = getattr(this, "alt", None)
                if not isinstance(alt, str):
                    alt = None
            if alt is None:
                alt = PRIMARY_ALT

        # This is already a global variable but we can inject it as a
        # local override if available.
        if pad is None:
            ctx = get_ctx()
            if ctx is not None:
                pad = ctx.pad
        if pad is not None:
            values["site"] = pad
        if this is not None:
            values["this"] = this
        if alt is not None:
            values["alt"] = alt
        self.plugin_controller.emit(
            "process-template-context", context=values, template=template
        )
        return values

    @staticmethod
    def select_jinja_autoescape(filename):
        if filename is None:
            return False
        return filename.endswith((".html", ".htm", ".xml", ".xhtml"))

    def resolve_custom_url_path(self, obj, url_path):
        for resolver in self.custom_url_resolvers:
            rv = resolver(obj, url_path)
            if rv is not None:
                return rv
        return None

    # -- methods for the plugin system

    def add_build_program(self, cls, program):
        self.build_programs.append((cls, program))

    def add_asset_type(self, asset_cls, build_program):
        self.build_programs.append((asset_cls, build_program))
        self.special_file_assets[asset_cls.source_extension] = asset_cls
        if asset_cls.artifact_extension:
            cext = asset_cls.source_extension + asset_cls.artifact_extension
            self.special_file_suffixes[cext] = asset_cls.source_extension

    def add_publisher(self, scheme, publisher):
        if scheme in self.publishers:
            raise RuntimeError('Scheme "%s" is already registered.' % scheme)
        self.publishers[scheme] = publisher

    def add_type(self, type):
        name = type.name
        if name in self.types:
            raise RuntimeError('Type "%s" is already registered.' % name)
        self.types[name] = type

    def virtualpathresolver(self, prefix):
        def decorator(func):
            if prefix in self.virtual_sources:
                raise RuntimeError('Prefix "%s" is already registered.' % prefix)
            self.virtual_sources[prefix] = func
            return func

        return decorator

    def urlresolver(self, func):
        self.custom_url_resolvers.append(func)
        return func

    def generator(self, func):
        self.custom_generators.append(func)
        return func
