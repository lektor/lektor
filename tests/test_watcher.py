import functools

import py
import pytest
from watchdog.observers.api import BaseObserver
from watchdog.observers.polling import PollingObserver

from lektor import utils
from lektor.watcher import BasicWatcher
from lektor.watcher import Watcher


def test_is_interesting(env):
    # pylint: disable=no-member
    cache_dir = py.path.local(utils.get_cache_dir())
    build_dir = py.path.local("build")

    w = Watcher(env, str(build_dir))

    # This partial makes the testing code shorter
    is_interesting = functools.partial(w.is_interesting, 0, "generic")

    assert is_interesting("a.file")
    assert not is_interesting(".file")
    assert not is_interesting(str(cache_dir / "another.file"))
    assert not is_interesting(str(build_dir / "output.file"))

    w.output_path = None
    assert is_interesting(str(build_dir / "output.file"))


class BrokenObserver(PollingObserver):
    # The InotifyObserver, when it fails due to insufficient system
    # inotify resources, does not fail until an attempt is made to start it.
    def start(self):
        raise OSError("crapout")


class TestBasicWatcher:
    # pylint: disable=no-self-use

    @pytest.fixture
    def paths(self, tmp_path):
        return [str(tmp_path)]

    def test_creates_observer(self, paths):
        with BasicWatcher(paths) as watcher:
            assert isinstance(watcher.observer, BaseObserver)

    def test_default_observer_broken(self, paths, capsys):
        observer_classes = (BrokenObserver, PollingObserver)
        with BasicWatcher(paths, observer_classes=observer_classes) as watcher:
            assert watcher.observer.__class__ is PollingObserver
        assert "crapout" in capsys.readouterr().out

    def test_default_observer_is_polling(self, paths, capsys):
        observer_classes = (BrokenObserver, BrokenObserver)
        with pytest.raises(OSError, match=r"crapout"):
            with BasicWatcher(paths, observer_classes=observer_classes):
                pass
        assert capsys.readouterr() == ("", "")

    def test_perverse_usage(self, paths):
        # This exercises a bug which occurred when BasicWatcher was
        # called with repeated (failing) values in observer_classes.
        observer_classes = (BrokenObserver, BrokenObserver, PollingObserver)
        with BasicWatcher(paths, observer_classes=observer_classes) as watcher:
            assert isinstance(watcher.observer, BaseObserver)

    def test_raises_error_if_started_twice(self, paths):
        with BasicWatcher(paths) as watcher:
            with pytest.raises(RuntimeError, match="already started"):
                watcher.start()
