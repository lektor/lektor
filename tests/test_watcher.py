import functools
import queue
import threading

import py
import pytest
from watchdog.observers.api import BaseObserver
from watchdog.observers.polling import PollingObserver

from lektor import utils
from lektor.watcher import BasicWatcher
from lektor.watcher import watch
from lektor.watcher import Watcher


class IterateInThread(threading.Thread):
    """Iterate iterable in a separate thread.

    This is a iterator which yields the results of the iterable.
    I.e. mostly, it's transparent.

    The results are passed back to the calling thread via a queue.  If
    the queue remains empty for a bit of time a `Timeout` exception
    will be raised.

    The timeout prevents the test from getting hung when expected
    results are not forthcoming.

    """

    timeout = 2.0

    def __init__(self, it):
        threading.Thread.__init__(self, daemon=True)
        self.it = it
        self.queue = queue.Queue()
        self.start()

    def run(self):
        for item in self.it:
            self.queue.put(item)

    def __next__(self):
        try:
            return self.queue.get(timeout=self.timeout)
        except queue.Empty:
            return pytest.fail("Timed out waiting for iterator")


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

    def test_iter(self, tmp_path):
        file1 = tmp_path / "file1"
        file1.touch()

        with BasicWatcher([str(tmp_path)]) as watcher:
            it = IterateInThread(watcher)

            file2 = tmp_path / "file2"
            file2.touch()
            # Check that we get notified about file2
            _, event_type, path = next(it)
            print(event_type, path)
            while path != str(file2):
                # On MacOS, for whatever reason, we get events about
                # the creation of tmp_path and file1.  Skip them.
                _, event_type, path = next(it)
                print(event_type, path)

            file1_renamed = tmp_path / "file1_renamed"
            file1.rename(file1_renamed)
            # Check for notification of renamed file.
            while path != str(file1_renamed):
                # Depending on platform, we may get more than one
                # event for file1. (E.g. on Linux we get both a
                # 'created' and a 'closed' event.)
                # (Also, on MacOS, for reasons not understood,
                # we appear to get a 'created' event for file1.)
                _, event_type, path = next(it)
                print(event_type, path)

            assert it.queue.empty()


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


def test_watch(env, mocker):
    Watcher = mocker.patch("lektor.watcher.Watcher")
    event1 = mocker.sentinel.event1

    def events():
        yield event1
        raise KeyboardInterrupt()

    watcher = Watcher.return_value.__enter__.return_value
    watcher.__iter__.return_value = events()

    assert list(watch(env)) == [event1]
