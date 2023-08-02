from __future__ import annotations

import os
import shutil
import sys
import threading
import warnings
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Callable
from typing import Generator

import pytest
from watchfiles import Change

from lektor.environment import Environment
from lektor.project import Project
from lektor.watcher import watch_project
from lektor.watcher import WatchFilter


RunInThread = Callable[[Callable[[], None]], None]


@pytest.fixture
def run_in_thread() -> RunInThread:
    threads = []

    def run_thread(target: Callable[[], None]) -> None:
        t = threading.Thread(target=target)
        t.start()
        threads.append(t)

    try:
        yield run_thread
    finally:
        for t in threads:
            t.join(10.0)
        for t in threads:
            assert not t.is_alive()


@dataclass
class WatchResult:
    change_seen: bool = False

    def __bool__(self):
        return self.change_seen


@dataclass
class WatcherTest:
    env: Environment
    run_in_thread: RunInThread

    @contextmanager
    def __call__(
        self,
        timeout: float = 1.2,
    ) -> Generator[WatchResult, None, None]:
        """Run watch_project in a separate thread, wait for a file change event.

        This is a context manager that runs watch_project in a separate thread.
        After the context exits, it will wait at most ``timeout`` seconds before returning.
        If a file system change is seen, it will return immediately.

        The context manager returns a WatchResult value.  After the context has been
        exited, the result will be True-ish if a file system change was noticed,
        False-ish otherwise.

        """
        if sys.platform == "darwin":
            self.macos_pause_for_calm()

        with self.watch(timeout) as change_seen:
            yield change_seen

    @contextmanager
    def watch(
        self,
        timeout: float,
    ) -> Generator[WatchResult, None, None]:
        """Run watch_project in a separate thread, wait for a file change event."""
        running = threading.Event()
        stop = threading.Event()
        changed = threading.Event()

        def run() -> None:
            watcher = watch_project(
                self.env, "non-existant-output-path", stop_event=stop
            )
            running.set()
            for _ in watcher:
                changed.set()
                return

        self.run_in_thread(run)
        result = WatchResult()
        running.wait()
        try:
            yield result
            result.change_seen = changed.wait(timeout)
        finally:
            stop.set()

    def macos_pause_for_calm(self) -> None:
        # Wait a bit for the dust to settle.
        # For whatever reason, on macOS, the watcher sometimes seems to return
        # filesystem events that happened shortly before it was started.
        for n in range(5):
            with self.watch(timeout=0.1) as change_seen:
                pass
            if not change_seen:
                break
            warnings.warn(f"macOS settle loop {n}: {change_seen}")  # noqa: B028


@pytest.fixture
def watcher_test(scratch_env: Environment, run_in_thread: RunInThread) -> WatcherTest:
    return WatcherTest(scratch_env, run_in_thread)


@pytest.fixture
def watched_path(scratch_env: Environment) -> Path:
    return Path(scratch_env.root_path)


def test_watcher_test(watcher_test: WatcherTest) -> None:
    with watcher_test(timeout=0.2) as change_seen:
        pass
    assert not change_seen


def test_sees_created_file(watcher_test: WatcherTest, watched_path: Path) -> None:
    with watcher_test() as change_seen:
        Path(watched_path, "created").touch()
    assert change_seen


def test_sees_deleted_file(watcher_test: WatcherTest, watched_path: Path) -> None:
    deleted_path = watched_path / "deleted"
    deleted_path.touch()

    with watcher_test() as change_seen:
        deleted_path.unlink()
    assert change_seen


def test_sees_modified_file(watcher_test: WatcherTest, watched_path: Path) -> None:
    modified_path = watched_path / "modified"
    modified_path.touch()

    with watcher_test() as change_seen:
        with modified_path.open("a") as fp:
            fp.write("addition")
    assert change_seen


def test_sees_file_moved_in(
    watcher_test: WatcherTest, watched_path: Path, tmp_path: Path
) -> None:
    orig_path = tmp_path / "orig_path"
    orig_path.touch()
    final_path = watched_path / "final_path"

    with watcher_test() as change_seen:
        orig_path.rename(final_path)
    assert change_seen


def test_sees_file_moved_out(
    watcher_test: WatcherTest, watched_path: Path, tmp_path: Path
) -> None:
    orig_path = watched_path / "orig_path"
    orig_path.touch()
    final_path = tmp_path / "final_path"

    with watcher_test() as change_seen:
        orig_path.rename(final_path)
    assert change_seen


def test_sees_deleted_directory(watcher_test: WatcherTest, watched_path: Path) -> None:
    # We only really care about deleted directories that contain at least a file.
    deleted_path = watched_path / "deleted"
    deleted_path.mkdir()
    watched_file = deleted_path / "file"
    watched_file.touch()

    with watcher_test() as change_seen:
        shutil.rmtree(deleted_path)
    assert change_seen


def test_sees_file_in_directory_moved_in(
    watcher_test: WatcherTest, watched_path: Path, tmp_path: Path
) -> None:
    # We only really care about directories that contain at least a file.
    orig_dir_path = tmp_path / "orig_dir_path"
    orig_dir_path.mkdir()
    Path(orig_dir_path, "file").touch()
    final_dir_path = watched_path / "final_dir_path"

    with watcher_test() as change_seen:
        orig_dir_path.rename(final_dir_path)
    assert change_seen


def test_sees_directory_moved_out(
    watcher_test: WatcherTest, watched_path: Path, tmp_path: Path
) -> None:
    # We only really care about directories that contain at least one file.
    orig_dir_path = watched_path / "orig_dir_path"
    orig_dir_path.mkdir()
    Path(orig_dir_path, "file").touch()
    final_dir_path = tmp_path / "final_dir_path"

    with watcher_test() as change_seen:
        orig_dir_path.rename(final_dir_path)
    assert change_seen


def test_ignores_opened_file(watcher_test: WatcherTest, watched_path: Path) -> None:
    file_path = watched_path / "file"
    file_path.touch()

    with watcher_test() as change_seen:
        with file_path.open() as fp:
            fp.read()
    assert not change_seen


@pytest.fixture(scope="session")
def watch_filter(project: Project) -> WatchFilter:
    env = Environment(project, load_plugins=False)
    return WatchFilter(env)


@pytest.mark.parametrize("path", [".dotfile", "webpack/node_modules"])
def test_WatchFilter_false(
    watch_filter: WatchFilter, path: str, project: Project
) -> None:
    abspath = os.path.abspath(os.path.join(project.tree, path))
    assert not watch_filter(Change.added, abspath)
