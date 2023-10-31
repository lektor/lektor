from __future__ import annotations

import posixpath
from typing import TYPE_CHECKING
from urllib.parse import parse_qsl
from urllib.parse import urlsplit
from weakref import ref as weakref

from lektor.constants import PRIMARY_ALT
from lektor.context import ignore_url_unaffecting_dependencies
from lektor.reporter import reporter
from lektor.utils import is_path_child_of
from lektor.utils import join_path

if TYPE_CHECKING:
    from lektor.db import Pad


class SourceObject:
    source_classification = "generic"

    # We consider this class at least what public usage is to considered
    # to be from another place.
    __module__ = "db"

    def __init__(self, pad: Pad):
        self._pad = weakref(pad)

    @property
    def alt(self):
        """Returns the effective alt of this source object (unresolved)."""
        return PRIMARY_ALT

    @property
    def source_filename(self):
        """The primary source filename of this source object.

        In general, subclasses should implement/override ``iter_source_filenames``
        rather than this property.
        """
        source_filenames = self.iter_source_filenames()
        return next(iter(source_filenames), None)

    is_hidden = False
    is_discoverable = True

    @property
    def is_visible(self):
        """The negated version of :attr:`is_hidden`."""
        return not self.is_hidden

    @property
    def is_undiscoverable(self):
        """The negated version of :attr:`is_discoverable`."""
        return not self.is_discoverable

    def iter_source_filenames(self):
        """An iterable of the source filenames for this source object.

        The first returned filename should be the "primary" one.
        """
        # pylint: disable=no-self-use
        return ()

    @property
    def url_path(self):
        """The URL path of this source object if available."""
        raise NotImplementedError()

    @property
    def path(self):
        """Return the full path to the source object.  Not every source
        object actually has a path but source objects without paths need
        to subclass `VirtualSourceObject`.
        """
        return None

    @property
    def pad(self) -> Pad:
        """The associated pad of this source object."""
        rv = self._pad()
        if rv is not None:
            return rv
        raise AttributeError("The pad went away")

    def resolve_url_path(self, url_path):
        """Given a URL path as list this resolves the most appropriate
        direct child and returns the list of remaining items.  If no
        match can be found, the result is `None`.
        """
        if not url_path:
            return self
        return None

    def is_child_of(self, path, strict=False):
        """Checks if the current object is a child of the passed object
        or path.
        """
        if isinstance(path, SourceObject):
            path = path.path
        if self.path is None or path is None:
            return False
        return is_path_child_of(self.path, path, strict=strict)

    def url_to(
        self,
        path,  # : Union[str, "SourceObject", "SupportsUrlPath"]
        alt: str | None = None,
        absolute: bool | None = None,
        external: bool | None = None,
        base_url: str | None = None,
        resolve: bool | None = None,
        strict_resolve: bool | None = None,
    ) -> str:
        """Calculates the URL from the current source object to the given
        other source object.  Alternatively a path can also be provided
        instead of a source object.  If the path starts with a leading
        bang (``!``) then no resolving is performed.

        If a `base_url` is provided then it's used instead of the URL of
        the record itself.

        If path is a string and resolve=False is passed, then no attempt is
        made to resolve the path to a Lektor source object.

        If path is a string and strict_resolve=True is passed, then an exception
        is raised if the path can not be resolved to a Lektor source object.

        API CHANGE: It used to be (lektor <= 3.3.1) that if absolute was true-ish,
        then a url_path (URL path relative to the site's ``base_path`` was returned.
        This is changed so that now an absolute URL path is returned.
        """
        if base_url is None:
            base_url = self.url_path
        if absolute:
            # This sort of reproduces the old behaviour, where when
            # ``absolute`` was trueish, the "absolute" URL path
            # (relative to config.base_path) was returned, regardless
            # of the value of ``external``.
            external = False
        if resolve is None and strict_resolve:
            resolve = True

        if isinstance(path, SourceObject):
            # assert not isinstance(path, Asset)
            target = path
            if alt is not None and alt != target.alt:
                # NB: path.path includes page_num
                alt_target = self.pad.get(path.path, alt=alt, persist=False)
                if alt_target is not None:
                    target = alt_target
                # FIXME: issue warning or fail if cannot get correct alt?
            url_path = target.url_path
        elif hasattr(path, "url_path"):  # e.g. Thumbnail
            assert path.url_path.startswith("/")
            url_path = path.url_path
        elif path[:1] == "!":
            # XXX: error if used with explicit alt?
            if resolve:
                raise RuntimeError("Resolve=True is incompatible with '!' prefix.")
            url_path = _join_url_path(self, path[1:])
        elif resolve is not None and not resolve:
            # XXX: error if used with explicit alt?
            url_path = _join_url_path(self, path)
        else:
            with ignore_url_unaffecting_dependencies():
                return self._resolve_url(
                    path,
                    alt=alt,
                    absolute=absolute,
                    external=external,
                    base_url=base_url,
                    strict=strict_resolve,
                )

        return self.pad.make_url(url_path, base_url, absolute, external)

    def _resolve_url(
        self,
        _url: str,
        alt: str | None,
        absolute: bool | None,
        external: bool | None,
        base_url: str | None,
        strict: bool | None,
    ) -> str:
        """Resolve (possibly relative) URL or db path to URL."""
        url = urlsplit(_url)
        if url.scheme or url.netloc:
            resolved = url
        else:
            # Interpret path as (possibly relative) db-path
            dbpath = join_path(self.path, url.path)
            params = dict(parse_qsl(url.query, keep_blank_values=False))
            query_alt = params.get("alt")
            # XXX: support page_num in query, too?
            if not alt:
                alt = query_alt or self.alt
            elif query_alt and query_alt != alt:
                raise RuntimeError("Conflicting values for alt.")
            target = self.pad.get(dbpath, alt=alt)
            if target is not None:
                url_path = target.url_path
                query = ""
            elif strict:
                raise RuntimeError(f"Can not resolve link {_url!r}")
            else:
                # Fall back to interpreting path as (possibly relative) URL path
                url_path = _join_url_path(self, url.path)
                query = url.query

            result = self.pad.make_url(
                url_path, absolute=absolute, external=external, base_url=base_url
            )
            resolved = urlsplit(result)._replace(query=query, fragment=url.fragment)
        return resolved.geturl()

    @property
    def url_content_path(self):
        """URL path to the directory that contains children of this source object.

        For container types, the record's ``url_content_path`` is often
        the same as its ``url_path``. The exception to this is when
        the page's slug contains a dot (".").
        See https://www.getlektor.com/docs/content/urls/#content-below-dotted-slugs

        The ``url_content_path`` should be ``None`` for attachments and other
        SourceObject types that can not contain child source objects.
        """
        return None


def _join_url_path(source, path):
    """Join possibly relative url path relative to source.url_content_path."""
    if posixpath.isabs(path):
        return path
    content_path = source.url_content_path
    if content_path is None:
        # Source is not a container type (e.g. it is an attachment).
        # Punt and treat path as relative to the source's containing directory.
        content_path = posixpath.dirname(source.url_path) or "/"
        reporter.report_generic(
            f"Suspicious use of relative URL {path!r} from non-container source {source!r}"
        )
    return posixpath.join(content_path, path)


class DBSourceObject(SourceObject):
    """This is the base class for objects that live in the lektor db.

    I.e. this is the type of object returned by pad.get().

    """

    @property
    def path(self):
        """Return the full database path to the source object.

        All DBSourceObjects must have paths.
        """
        raise NotImplementedError()

    # XXX: move SourceObject.url_to here?

    def __eq__(self, other):
        if other is self:
            return True  # optimization
        if other.__class__ is not self.__class__:
            return False  # optimization
        return (
            other.alt == self.alt and other.path == self.path and other.pad == self.pad
        )

    def __hash__(self):
        return hash((self.path, self.alt))


class VirtualSourceObject(DBSourceObject):
    """Virtual source objects live below a parent record but do not
    originate from the source tree with a separate file.
    """

    def __init__(self, record):
        super().__init__(record.pad)
        self.record = record

    @property
    def path(self):
        raise NotImplementedError()

    def get_mtime(self, path_cache):
        # pylint: disable=no-self-use
        return None

    def get_checksum(self, path_cache):
        # pylint: disable=no-self-use
        return None

    @property
    def parent(self):
        return self.record

    @property
    def alt(self):
        return self.record.alt

    def iter_source_filenames(self):
        # This is a default.  However, if artifacts produced from a
        # particular virtual source type do not explicitly vary with
        # the parent record, it may make sense to override this to
        # return an empty (or some other) list of file names.
        return self.record.iter_source_filenames()
