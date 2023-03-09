import functools
import os
import shutil
import sys
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from typing import Generator
from typing import Optional
from typing import Type

import py
import pytest
from watchdog.observers.api import BaseObserver
from watchdog.observers.polling import PollingObserver

from lektor import utils
from lektor.watcher import BasicWatcher
from lektor.watcher import watch
from lektor.watcher import Watcher


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


@dataclass
class WatcherTest:
    watched_path: Path

    @contextmanager
    def __call__(
        self,
        observer_class: Optional[Type[BaseObserver]] = None,
        should_set_event: bool = True,
        timeout: float = 1.2,
    ) -> Generator[Path, None, None]:

        kwargs: dict[str, Any] = {}
        if observer_class is not None:
            kwargs.update(
                observer_classes=(observer_class,),
                observer_timeout=0.1,  # fast polling timer to speed tests
            )

        with BasicWatcher([os.fspath(self.watched_path)], **kwargs) as watcher:
            event = threading.Event()

            class WatcherWatcher(threading.Thread):
                # iterate watcher in a separate thread
                def run(self):
                    for _ in watcher:
                        event.set()

            WatcherWatcher(daemon=True).start()

            if sys.platform == "darwin":
                # The FSEventObserver (used on macOS) seems to send events for things that
                # happened before is was started.  Here, we wait a little bit for things to
                # start, then discard any pre-existing events.
                time.sleep(0.1)
                event.clear()

            yield self.watched_path

            if should_set_event:
                assert event.wait(timeout)
            else:
                assert not event.wait(timeout)


@pytest.fixture(
    params=[
        pytest.param(None, id="default observer"),
        PollingObserver,
    ]
)
def observer_class(request: pytest.FixtureRequest) -> bool:
    return request.param


@pytest.fixture
def watcher_test(tmp_path: Path) -> WatcherTest:
    watched_path = tmp_path / "watched_path"
    watched_path.mkdir()
    return WatcherTest(watched_path)


def test_watcher_test(watcher_test: WatcherTest) -> None:
    with watcher_test(should_set_event=False, timeout=0.2):
        pass


def test_BasicWatcher_sees_created_file(
    watcher_test: WatcherTest, observer_class: Optional[Type[BaseObserver]]
) -> None:
    with watcher_test(observer_class=observer_class) as watched_path:
        Path(watched_path, "created").touch()


def test_BasicWatcher_sees_deleted_file(
    watcher_test: WatcherTest, observer_class: Optional[Type[BaseObserver]]
) -> None:
    deleted_path = watcher_test.watched_path / "deleted"
    deleted_path.touch()

    with watcher_test(observer_class=observer_class):
        deleted_path.unlink()


def test_BasicWatcher_sees_modified_file(
    watcher_test: WatcherTest, observer_class: Optional[Type[BaseObserver]]
) -> None:
    modified_path = watcher_test.watched_path / "modified"
    modified_path.touch()

    with watcher_test(observer_class=observer_class):
        with modified_path.open("a") as fp:
            fp.write("addition")


def test_BasicWatcher_sees_file_moved_in(
    watcher_test: WatcherTest,
    observer_class: Optional[Type[BaseObserver]],
    tmp_path: Path,
) -> None:
    orig_path = tmp_path / "orig_path"
    orig_path.touch()
    final_path = watcher_test.watched_path / "final_path"

    with watcher_test(observer_class=observer_class):
        orig_path.rename(final_path)


def test_BasicWatcher_sees_file_moved_out(
    watcher_test: WatcherTest,
    observer_class: Optional[Type[BaseObserver]],
    tmp_path: Path,
) -> None:
    orig_path = watcher_test.watched_path / "orig_path"
    orig_path.touch()
    final_path = tmp_path / "final_path"

    with watcher_test(observer_class=observer_class):
        orig_path.rename(final_path)


def test_BasicWatcher_sees_deleted_directory(
    watcher_test: WatcherTest, observer_class: Optional[Type[BaseObserver]]
) -> None:
    # We only really care about deleted directories that contain at least a file.
    deleted_path = watcher_test.watched_path / "deleted"
    deleted_path.mkdir()
    watched_file = deleted_path / "file"
    watched_file.touch()

    with watcher_test(observer_class=observer_class):
        shutil.rmtree(deleted_path)


def test_BasicWatcher_sees_file_in_directory_moved_in(
    watcher_test: WatcherTest,
    observer_class: Optional[Type[BaseObserver]],
    tmp_path: Path,
) -> None:
    # We only really care about directories that contain at least a file.
    orig_dir_path = tmp_path / "orig_dir_path"
    orig_dir_path.mkdir()
    Path(orig_dir_path, "file").touch()
    final_dir_path = watcher_test.watched_path / "final_dir_path"

    with watcher_test(observer_class=observer_class):
        orig_dir_path.rename(final_dir_path)


def test_BasicWatcher_sees_directory_moved_out(
    watcher_test: WatcherTest,
    observer_class: Optional[Type[BaseObserver]],
    tmp_path: Path,
) -> None:
    # We only really care about directories that contain at least one file.
    orig_dir_path = watcher_test.watched_path / "orig_dir_path"
    orig_dir_path.mkdir()
    Path(orig_dir_path, "file").touch()
    final_dir_path = tmp_path / "final_dir_path"

    with watcher_test(observer_class=observer_class):
        orig_dir_path.rename(final_dir_path)


def test_BasicWatcher_ignores_opened_file(watcher_test: WatcherTest) -> None:
    file_path = watcher_test.watched_path / "file"
    file_path.touch()

    with watcher_test(should_set_event=False):
        with file_path.open() as fp:
            fp.read()


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
