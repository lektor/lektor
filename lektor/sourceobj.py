import posixpath
from abc import ABC
from abc import abstractmethod
from typing import cast
from typing import ClassVar
from typing import Iterator
from typing import Optional
from typing import Sequence
from typing import TYPE_CHECKING
from typing import Union
from weakref import ref as weakref

from lektor.constants import PRIMARY_ALT
from lektor.typing.db import Alt
from lektor.typing.db import DbPath
from lektor.utils import is_path_child_of
from lektor.utils import join_path

if TYPE_CHECKING:  # circdep
    from lektor.builder import PathCache
    from lektor.db import Pad
    from lektor.db import Record


class SourceObject(ABC):
    source_classification: ClassVar[str] = "generic"

    # We consider this class at least what public usage is to considered
    # to be from another place.
    __module__ = "db"

    def __init__(self, pad: "Pad") -> None:
        self._pad = weakref(pad)

    @property
    def alt(self) -> Alt:
        """Returns the effective alt of this source object (unresolved)."""
        return PRIMARY_ALT

    @property
    def source_filename(self) -> str:
        """The primary source filename of this source object."""

    is_hidden = False
    is_discoverable = True

    @property
    def is_visible(self) -> bool:
        """The negated version of :attr:`is_hidden`."""
        return not self.is_hidden

    @property
    def is_undiscoverable(self) -> bool:
        """The negated version of :attr:`is_discoverable`."""
        return not self.is_discoverable

    def iter_source_filenames(self) -> Iterator[str]:
        fn = self.source_filename
        if fn is not None:
            yield self.source_filename

    @property
    def url_path(self) -> str:
        """The URL path of this source object if available."""
        raise NotImplementedError

    @property
    def pad(self) -> "Pad":
        """The associated pad of this source object."""
        rv = self._pad()
        if rv is not None:
            return rv
        raise AttributeError("The pad went away")

    def resolve_url_path(self, url_path: Sequence[str]) -> Optional["SourceObject"]:
        """Given a URL path as list this resolves the most appropriate
        direct child and returns the list of remaining items.  If no
        match can be found, the result is `None`.
        """
        if not url_path:
            return self
        return None


class DbSourceObject(SourceObject):
    """This is the base class for objects live in the lektor db.

    I.e. This is the type of object returned by by pad.get().
    """

    @property
    @abstractmethod
    def path(self) -> DbPath:
        """Return the full path to the source object.  Not every source
        object actually has a path but source objects without paths need
        to subclass `VirtualSourceObject`.
        """
        # FIXME: I'm not sure the docstring is right.
        # VirtualSourceObjects need to have paths, I think.
        # (Assets do not have paths.)
        # (This is the db path).

    def iter_virtual_sources(self) -> Iterator["VirtualSourceObject"]:
        # pylint: disable=no-self-use
        return iter([])

    def url_to(
        self,
        path: Union["DbSourceObject", str, object],
        alt: Optional[Alt] = None,
        absolute: Optional[bool] = None,
        external: Optional[bool] = None,
        base_url: Optional[str] = None,
    ) -> str:
        """Calculates the URL from the current source object to the given
        other source object.  Alternatively a path can also be provided
        instead of a source object.  If the path starts with a leading
        bang (``!``) then no resolving is performed.

        If a `base_url` is provided then it's used instead of the URL of
        the record itself.
        """
        if isinstance(path, DbSourceObject):
            # API: Used to re-resolve path to source to path. Unnecessary?
            url_path = path.url_path
        elif isinstance(path, str) and path[:1] == "!":
            url_path = posixpath.join(self.url_path, path[1:])
        else:
            # Attempt to use path as a relative db-path and resolve
            # to url_path
            #
            # NB: Need to stringify here to support passing imagetools.Thumbnail as path.
            # That should probably be typed more explicit.
            str_path = str(path)
            if str_path.startswith("/"):
                dbpath = cast(DbPath, str_path)
            else:
                dbpath = join_path(self.path, str_path)  # absolute db-path
            source = self.pad.get(dbpath, alt=alt or self.alt)
            if source is not None:
                url_path = source.url_path
            else:
                # Failed to resolve db-path to url-path (as requested)
                # FIXME: should issue a warning here?
                url_path = posixpath.join(self.url_path, str_path)

        if absolute:
            return url_path
        if base_url is None:
            base_url = self.url_path
        return self.pad.make_url(url_path, base_url, absolute, external)

    def is_child_of(
        self, path: Union[DbPath, "DbSourceObject"], strict: bool = False
    ) -> bool:
        """Checks if the current object is a child of the passed object
        or path.
        """
        if isinstance(path, SourceObject):
            path_ = path.path
        else:
            path_ = path

        if self.path is None or path_ is None:
            return False
        return is_path_child_of(self.path, path_, strict=strict)


class VirtualSourceObject(DbSourceObject):
    """Virtual source objects live below a parent record but do not
    originate from the source tree with a separate file.
    """

    def __init__(self, record: "Record"):
        super().__init__(record.pad)
        self.record = record

    def get_mtime(self, path_cache: "PathCache") -> Optional[float]:
        # pylint: disable=no-self-use
        return None

    def get_checksum(self, path_cache: "PathCache") -> Optional[str]:
        # pylint: disable=no-self-use
        return None

    @property
    def parent(self) -> DbSourceObject:
        return self.record

    @property
    def alt(self) -> Alt:
        return self.record.alt

    @property
    def source_filename(self) -> str:  # FIXME: narrower type (builder.SourceFilename?)
        return self.record.source_filename

    def iter_virtual_sources(self) -> Iterator["VirtualSourceObject"]:
        yield self
