import os
import stat
import sys
import tempfile
from functools import partial
from itertools import chain


def _ensure_tree_writeable(path: str) -> None:
    """Attempt to ensure that all files in the tree rooted at path are writeable."""
    dirscans = []

    def fix_mode(path, statfunc):
        try:
            # paranoia regarding symlink attacks
            current_mode = statfunc(follow_symlinks=False).st_mode
            if not stat.S_ISLNK(current_mode):
                isdir = stat.S_ISDIR(current_mode)
                fixed_mode = current_mode | (0o700 if isdir else 0o200)
                if current_mode != fixed_mode:
                    os.chmod(path, fixed_mode)
                if isdir:
                    dirscans.append(os.scandir(path))
        except FileNotFoundError:
            pass

    fix_mode(path, partial(os.stat, path))
    for entry in chain.from_iterable(dirscans):
        fix_mode(entry.path, entry.stat)


class FixedTemporaryDirectory(tempfile.TemporaryDirectory):
    """A version of tempfile.TemporaryDirectory that works if dir contains read-only files.

    On python < 3.8 under Windows, if any read-only files are created
    in a TemporaryDirectory, TemporaryDirectory will throw an
    exception when it tries to remove them on cleanup. See
    https://bugs.python.org/issue26660

    This can create issues, e.g., with temporary git repositories since
    git creates read-only files in its object store.

    """

    def cleanup(self) -> None:
        _ensure_tree_writeable(self.name)
        super().cleanup()


if sys.version_info >= (3, 8):
    TemporaryDirectory = tempfile.TemporaryDirectory
else:
    TemporaryDirectory = FixedTemporaryDirectory
