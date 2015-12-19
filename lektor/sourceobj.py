import posixpath

from weakref import ref as weakref
from lektor.environment import PRIMARY_ALT
from lektor.utils import make_relative_url, cleanup_path


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

    @property
    def is_visible(self):
        """The negated version of :attr:`is_hidden`."""
        return not self.is_hidden

    def iter_source_filenames(self):
        fn = self.source_filename
        if fn is not None:
            yield self.source_filename

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
        this_path = cleanup_path(self.path).split('/')
        crumbs = cleanup_path(path).split('/')
        return this_path[:len(crumbs)] == crumbs and \
            (not strict or len(this_path) > len(crumbs))

    def url_to(self, path, alt=None, absolute=False, external=False):
        """Calculates the URL from the current source object to the given
        other source object.  Alternatively a path can also be provided
        instead of a source object.  If the path starts with a leading
        bang (``!``) then no resolving is performed.
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
            source = self.pad.get(posixpath.join(self.path, path), alt=alt)
            if source is not None:
                path = source.url_path

        if absolute:
            return path
        elif external:
            return self.pad.make_absolute_url(path)
        return make_relative_url(self.url_path, path)


class VirtualSourceObject(SourceObject):
    """Virtual source objects live below a parent record but do not
    originate from the source tree with a separate file.
    """

    def __init__(self, parent):
        SourceObject.__init__(self, parent.pad)
        self.parent = parent

    def is_child_of(self, path, strict=False):
        # cannot be strict going down
        return self.parent.is_child_of(path, strict=False)

    @property
    def alt(self):
        return self.parent.alt

    @property
    def source_filename(self):
        return self.parent.source_filename
