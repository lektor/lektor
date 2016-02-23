import posixpath

from weakref import ref as weakref
from lektor.environment import PRIMARY_ALT
from lektor.utils import join_path, is_path_child_of


class SourceObject(object):
    source_classification = 'generic'

    # We consider this class at least what public usage is to considered
    # to be from another place.
    __module__ = 'db'

    def __init__(self, pad):
        self._pad = weakref(pad)

    @property
    def alt(self):
        """Returns the effective alt of this source object (unresolved)."""
        return PRIMARY_ALT

    @property
    def source_filename(self):
        """The primary source filename of this source object."""

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
        fn = self.source_filename
        if fn is not None:
            yield self.source_filename

    def iter_virtual_sources(self):
        return []

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
    def pad(self):
        """The associated pad of this source object."""
        rv = self._pad()
        if rv is not None:
            return rv
        raise AttributeError('The pad went away')

    def resolve_url_path(self, url_path):
        """Given a URL path as list this resolves the most appropriate
        direct child and returns the list of remaining items.  If no
        match can be found, the result is `None`.
        """
        if not url_path:
            return self

    def is_child_of(self, path, strict=False):
        """Checks if the current object is a child of the passed object
        or path.
        """
        if isinstance(path, SourceObject):
            path = path.path
        if self.path is None or path is None:
            return False
        return is_path_child_of(self.path, path, strict=strict)

    def url_to(self, path, alt=None, absolute=None, external=None,
               base_url=None):
        """Calculates the URL from the current source object to the given
        other source object.  Alternatively a path can also be provided
        instead of a source object.  If the path starts with a leading
        bang (``!``) then no resolving is performed.

        If a `base_url` is provided then it's used instead of the URL of
        the record itself.
        """
        if alt is None:
            alt = getattr(path, 'alt', None)
            if alt is None:
                alt = self.alt

        resolve = True
        path = getattr(path, 'url_path', path)
        if path[:1] == '!':
            resolve = False
            path = path[1:]

        if resolve:
            if not path.startswith('/'):
                if self.path is None:
                    raise RuntimeError('Cannot use relative URL generation '
                                       'from sources that do not have a '
                                       'path.  The source object without '
                                       'a path is %r' % self)
                path = join_path(self.path, path)
            source = self.pad.get(path, alt=alt)
            if source is not None:
                path = source.url_path
        else:
            path = posixpath.join(self.url_path, path)

        if absolute:
            return path
        if base_url is None:
            base_url = self.url_path
        return self.pad.make_url(path, base_url, absolute, external)


class VirtualSourceObject(SourceObject):
    """Virtual source objects live below a parent record but do not
    originate from the source tree with a separate file.
    """

    def __init__(self, record):
        SourceObject.__init__(self, record.pad)
        self.record = record

    @property
    def path(self):
        raise NotImplementedError()

    def get_mtime(self, path_cache):
        return None

    def get_checksum(self, path_cache):
        return None

    @property
    def parent(self):
        return self.record

    @property
    def alt(self):
        return self.record.alt

    @property
    def source_filename(self):
        return self.record.source_filename

    def iter_virtual_sources(self):
        yield self
