import os
import posixpath
import stat
from typing import cast
from typing import ClassVar
from typing import Iterator
from typing import Optional
from typing import overload
from typing import Sequence
from typing import TYPE_CHECKING

from lektor.sourceobj import SourceObject
from lektor.typing.db import ArtifactName
from lektor.typing.db import SourceFilename
from lektor.typing.db import UrlPath

if TYPE_CHECKING:
    from lektor.db import Pad


def get_asset(pad: "Pad", filename: str, parent: "Asset") -> Optional["Asset"]:
    # API: Used to default parent=None, but that case is not handled in the function body.
    return parent._get_child_asset(filename)


class Asset(SourceObject):
    # Source specific overrides.  The source_filename to none removes
    # the inherited descriptor.
    source_classification: ClassVar[str] = "asset"
    artifact_extension: ClassVar[str] = ""

    @overload
    def __init__(self, pad: "Pad", name: str, path: str) -> None:
        ...

    @overload
    def __init__(
        self, pad: "Pad", name: str, path: None = ..., parent: "Asset" = ...
    ) -> None:
        ...

    def __init__(
        self,
        pad: "Pad",
        name: str,
        path: Optional[str] = None,
        parent: Optional["Asset"] = None,
    ) -> None:
        SourceObject.__init__(self, pad)
        self.name = name
        self.parent = parent
        if parent:
            src_fn = os.path.join(parent.source_filename, name)
        else:
            assert path
            src_fn = path
        self._source_filename = cast(SourceFilename, src_fn)

    @property
    def source_filename(self) -> SourceFilename:
        return self._source_filename

    @property
    def url_name(self) -> str:
        name = self.name
        base, ext = posixpath.splitext(name)

        # If this is a known extension from an attachment then convert it
        # to lowercase
        if ext.lower() in self.pad.db.config["ATTACHMENT_TYPES"]:
            ext = ext.lower()

        return base + ext + self.artifact_extension

    @property
    def url_path(self) -> UrlPath:
        if self.parent is None:
            return UrlPath("/" + self.name)
        return UrlPath(posixpath.join(self.parent.url_path, self.url_name))

    @property
    def artifact_name(self) -> ArtifactName:
        if self.parent is not None:
            return cast(
                ArtifactName,
                self.parent.artifact_name.rstrip("/") + "/" + self.url_name,
            )
        return cast(ArtifactName, self.url_path)

    def build_asset(self, f):  # type: ignore
        # XXX: Unused?
        pass

    @property
    def children(self) -> Iterator["Asset"]:
        return iter(())

    def _get_child_asset(self, filename: str) -> Optional["Asset"]:
        env = self.pad.db.env

        if env.is_uninteresting_source_name(filename):
            return None

        try:
            stat_obj = os.stat(os.path.join(self.source_filename, filename))
        except OSError:
            return None
        if stat.S_ISDIR(stat_obj.st_mode):
            return Directory(self.pad, filename, parent=self)

        ext = os.path.splitext(filename)[1]
        cls = env.special_file_assets.get(ext, File)
        return cls(self.pad, filename, parent=self)

    def get_child(self, name: str, from_url: bool = False) -> Optional["Asset"]:
        # pylint: disable=no-self-use
        return None

    def resolve_url_path(self, url_path: Sequence[str]) -> Optional["Asset"]:
        if not url_path:
            return self
        # pylint: disable=assignment-from-none
        child = self.get_child(url_path[0], from_url=True)
        if child is not None:
            return child.resolve_url_path(url_path[1:])
        return None

    def __repr__(self) -> str:
        return "<%s %r>" % (
            self.__class__.__name__,
            self.artifact_name,
        )


class Directory(Asset):
    """Represents an asset directory."""

    @property
    def children(self) -> Iterator[Asset]:
        try:
            files = os.listdir(self.source_filename)
        except OSError:
            return

        for filename in files:
            asset = self.get_child(filename)
            if asset is not None:
                yield asset

    def get_child(self, name: str, from_url: Optional[bool] = False) -> Optional[Asset]:
        asset = get_asset(self.pad, name, parent=self)
        if asset is not None or not from_url:
            return asset

        # At this point it means we did not find a child yet, but we
        # came from an URL.  We can try to chop off product suffixes to
        # find the original source asset.  For instance a file called
        # foo.less.css will be reduced to foo.less.
        prod_suffix = "." + ".".join(name.rsplit(".", 2)[1:])
        ext = self.pad.db.env.special_file_suffixes.get(prod_suffix)
        if ext is not None:
            return get_asset(self.pad, name[: -len(prod_suffix)] + ext, parent=self)
        return None

    def resolve_url_path(self, url_path: Sequence[str]) -> Optional[Asset]:
        # Resolve "/path/" to "/path/index.html", as production servers do.
        if not url_path:
            index = self.get_child("index.html") or self.get_child("index.htm")
            if index is not None:
                return index

        return super().resolve_url_path(url_path)


class File(Asset):
    """Represents a static asset file."""
