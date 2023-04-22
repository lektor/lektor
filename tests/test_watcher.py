from __future__ import annotations

import os
import shutil
import threading
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Generator

import pytest
from watchfiles import Change

from lektor.environment import Environment
from lektor.project import Project
from lektor.watcher import watch_project
from lektor.watcher import WatchFilter


@dataclass
class WatcherTest:
    env: Environment

    @property
    def watched_path(self) -> Path:
        return Path(self.env.root_path)

    @contextmanager
    def __call__(
        self,
        should_set_event: bool = True,
        timeout: float = 1.2,
    ) -> Generator[Path, None, None]:

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

        t = threading.Thread(target=run)
        t.start()
        running.wait()
        try:
            yield self.watched_path
            changed.wait(timeout)
        finally:
            stop.set()
            t.join()

        if should_set_event:
            assert changed.is_set()
        else:
            assert not changed.is_set()


@pytest.fixture
def watcher_test(scratch_env: Environment) -> WatcherTest:
    return WatcherTest(scratch_env)


def test_watcher_test(watcher_test: WatcherTest) -> None:
    with watcher_test(should_set_event=False, timeout=0.2):
        pass


def test_sees_created_file(watcher_test: WatcherTest) -> None:
    with watcher_test() as watched_path:
        watched_path.joinpath("created").touch()


def test_sees_deleted_file(watcher_test: WatcherTest) -> None:
    deleted_path = watcher_test.watched_path / "deleted"
    deleted_path.touch()

    with watcher_test():
        deleted_path.unlink()


def test_sees_modified_file(watcher_test: WatcherTest) -> None:
    modified_path = watcher_test.watched_path / "modified"
    modified_path.touch()

    with watcher_test():
        with modified_path.open("a") as fp:
            fp.write("addition")


def test_sees_file_moved_in(watcher_test: WatcherTest, tmp_path: Path) -> None:
    orig_path = tmp_path / "orig_path"
    orig_path.touch()
    final_path = watcher_test.watched_path / "final_path"

    with watcher_test():
        orig_path.rename(final_path)


def test_sees_file_moved_out(watcher_test: WatcherTest, tmp_path: Path) -> None:
    orig_path = watcher_test.watched_path / "orig_path"
    orig_path.touch()
    final_path = tmp_path / "final_path"

    with watcher_test():
        orig_path.rename(final_path)


def test_sees_deleted_directory(watcher_test: WatcherTest) -> None:
    # We only really care about deleted directories that contain at least a file.
    deleted_path = watcher_test.watched_path / "deleted"
    deleted_path.mkdir()
    watched_file = deleted_path / "file"
    watched_file.touch()

    with watcher_test():
        shutil.rmtree(deleted_path)


def test_sees_file_in_directory_moved_in(
    watcher_test: WatcherTest, tmp_path: Path
) -> None:
    # We only really care about directories that contain at least a file.
    orig_dir_path = tmp_path / "orig_dir_path"
    orig_dir_path.mkdir()
    Path(orig_dir_path, "file").touch()
    final_dir_path = watcher_test.watched_path / "final_dir_path"

    with watcher_test():
        orig_dir_path.rename(final_dir_path)


def test_sees_directory_moved_out(watcher_test: WatcherTest, tmp_path: Path) -> None:
    # We only really care about directories that contain at least one file.
    orig_dir_path = watcher_test.watched_path / "orig_dir_path"
    orig_dir_path.mkdir()
    Path(orig_dir_path, "file").touch()
    final_dir_path = tmp_path / "final_dir_path"

    with watcher_test():
        orig_dir_path.rename(final_dir_path)


def test_ignores_opened_file(watcher_test: WatcherTest) -> None:
    file_path = watcher_test.watched_path / "file"
    file_path.touch()

    with watcher_test(should_set_event=False):
        with file_path.open() as fp:
            fp.read()


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
