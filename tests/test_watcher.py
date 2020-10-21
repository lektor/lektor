import functools

import py

from lektor import utils
from lektor import watcher


def test_is_interesting(env):
    # pylint: disable=no-member
    cache_dir = py.path.local(utils.get_cache_dir())
    build_dir = py.path.local("build")

    w = watcher.Watcher(env, str(build_dir))

    # This partial makes the testing code shorter
    is_interesting = functools.partial(w.is_interesting, 0, "generic")

    assert is_interesting("a.file")
    assert not is_interesting(".file")
    assert not is_interesting(str(cache_dir / "another.file"))
    assert not is_interesting(str(build_dir / "output.file"))

    w.output_path = None
    assert is_interesting(str(build_dir / "output.file"))
