from __future__ import annotations

import posixpath
import warnings
from collections import defaultdict
from contextlib import suppress
from itertools import takewhile
from operator import methodcaller
from pathlib import Path
from typing import Generator
from typing import Iterable
from typing import Sequence
from typing import TYPE_CHECKING

from werkzeug.utils import cached_property

from lektor.sourceobj import SourceObject
from lektor.utils import deprecated
from lektor.utils import DeprecatedWarning

if TYPE_CHECKING:
    from _typeshed import StrPath
    from lektor.db import Pad


def get_asset_root(pad: Pad, asset_roots: Iterable[StrPath]) -> Directory:
    """Get the merged asset root.

    This represents a logical merging or overlaying of (possibly) multiple asset trees,
    rooted at directories given by ``asset_roots``.

    Any paths listed in ``asset_roots`` that do not refer to a directory
    are silently ignored.
    """
    root_paths = tuple(
        Path(root).absolute() for root in asset_roots if Path(root).is_dir()
    )
    return Directory(pad, parent=None, name="", paths=root_paths)


@deprecated(version="3.4.0")
def get_asset(pad: Pad, filename: str, parent: Asset | None = None) -> Asset | None:
    if parent is None:
        parent = pad.asset_root
    else:
        assert pad is parent.pad
    return parent.get_child(filename)


_FROM_URL_DEPRECATED = DeprecatedWarning(
    "from_url",
    reason="The `from_url` parameter of `Asset.get_child` is now ignored.",
    version="3.4.0",
)


class Asset(SourceObject):
    source_classification = "asset"
    artifact_extension = ""

    def __init__(
        self, pad: Pad, name: str, parent: Asset | None, paths: tuple[Path, ...]
    ):
        super().__init__(pad)
        self.name = name
        self.parent = parent
        self._paths = paths

    def iter_source_filenames(self) -> Generator[str, None, None]:
        yield from map(str, self._paths)

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
    def url_path(self) -> str:
        if self.parent is None:
            return "/" + self.name
        return posixpath.join(self.parent.url_path, self.url_name)

    @property
    def artifact_name(self) -> str:
        if self.parent is not None:
            return self.parent.artifact_name.rstrip("/") + "/" + self.url_name
        return self.url_path

    @property
    def children(self) -> Iterable[Asset]:
        return ()

    # pylint: disable-next=no-self-use,useless-return
    def get_child(self, name: str, from_url: bool = False) -> Asset | None:
        if from_url:
            warnings.warn(_FROM_URL_DEPRECATED, stacklevel=2)
        return None

    def resolve_url_path(self, url_path: Sequence[str]) -> Asset | None:
        if len(url_path) == 0:
            return self
        return None

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {self.artifact_name!r}>"


class Directory(Asset):
    """Represents a merged set of asset directories."""

    @property
    def children(self) -> Iterable[Asset]:
        return self._children_by_name.values()

    def get_child(self, name: str, from_url: bool = False) -> Asset | None:
        if from_url:
            warnings.warn(_FROM_URL_DEPRECATED, stacklevel=2)
        return self._children_by_name.get(name)

    @cached_property
    def _children_by_name(self) -> dict[str, Asset]:
        return {asset.name: asset for asset in self._iter_children()}

    def _iter_children(self) -> Generator[Asset, None, None]:
        env = self.pad.env
        candidates_by_name = defaultdict(list)
        for path in self._paths:
            with suppress(OSError):
                for child in path.iterdir():
                    if not env.is_uninteresting_source_name(child.name):
                        candidates_by_name[child.name].append(child)

        for name, candidates in candidates_by_name.items():
            leading_dirs = tuple(takewhile(methodcaller("is_dir"), candidates))
            if leading_dirs:
                # Merge directories at the top of the overlay stack.
                #
                # Directories overlayed above a non-directory shadow (hide) that
                # non-directory.  (That non-directory, in turn, shadows anything under
                # it.)
                yield Directory(self.pad, parent=self, name=name, paths=leading_dirs)
            else:
                # If first candidate is not a directory, it shadows any below it.
                path = candidates[0]
                asset_class = env.special_file_assets.get(path.suffix, File)
                yield asset_class(self.pad, parent=self, name=name, paths=(path,))

    @property
    def url_name(self) -> str:
        return self.name + self.artifact_extension

    @property
    def url_path(self) -> str:
        path = super().url_path
        if not path.endswith("/"):
            path += "/"
        return path

    def resolve_url_path(self, url_path: Sequence[str]) -> Asset | None:
        if len(url_path) == 0:
            return self

        # Optimization: try common case where file extension has not been mangled
        child = self.get_child(url_path[0])
        if child is not None:
            return child.resolve_url_path(url_path[1:])

        if len(url_path) == 1:
            # There are a number of ways a file extension can be mangled to form the
            # url_path. (See `Asset.url_name`.) It can be lower-cased, and/or it could
            # have had `artifact_extension` appended.  It's not easy to check all these
            # cases individually, so we'll just look for a matching child.
            for child in self.children:
                if child.url_name == url_path[0]:
                    return child
        return None

    @property
    def url_content_path(self) -> str:
        return self.url_path


class File(Asset):
    """Represents a static asset file."""
