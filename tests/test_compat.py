import os
from pathlib import Path

import pytest

from lektor.compat import _ensure_tree_writeable
from lektor.compat import FixedTemporaryDirectory
from lektor.compat import TemporaryDirectory


def test_ensure_tree_writeable(tmp_path):
    topdir = tmp_path / "topdir"
    subdir = topdir / "subdir"
    regfile = subdir / "regfile"
    subdir.mkdir(parents=True)
    regfile.touch(mode=0)
    subdir.chmod(0)
    topdir.chmod(0)

    _ensure_tree_writeable(topdir)

    for p in topdir, subdir, regfile:
        assert os.access(p, os.W_OK)


@pytest.mark.parametrize("tmpdir_class", [FixedTemporaryDirectory, TemporaryDirectory])
def test_TemporaryDirectory(tmpdir_class):
    with tmpdir_class() as tmpdir:
        file = Path(tmpdir, "test-file")
        file.touch(mode=0)
        os.chmod(tmpdir, 0)
    assert not os.path.exists(tmpdir)
