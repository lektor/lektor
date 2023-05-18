from __future__ import annotations

import os
from typing import Any
from typing import Generator
from typing import TYPE_CHECKING

import watchfiles

from lektor.utils import get_cache_dir

if TYPE_CHECKING:
    from _typeshed import StrPath
    from lektor.environment import Environment


def watch_project(
    env: Environment, output_path: StrPath, **kwargs: Any
) -> Generator[set[watchfiles.FileChange], None, None]:
    """Watch project source files for changes.

    Returns an generator that yields sets of changes as they are noticed.

    Changes to files within ``output_path`` are ignored, along with other files
    deemed not to be Lektor source files.

    """
    watch_paths = [env.root_path, env.project.project_file, *env.theme_paths]
    ignore_paths = [os.path.abspath(p) for p in (get_cache_dir(), output_path)]
    watch_filter = WatchFilter(env, ignore_paths=ignore_paths)

    return watchfiles.watch(*watch_paths, watch_filter=watch_filter, **kwargs)


class WatchFilter(watchfiles.DefaultFilter):
    def __init__(self, env: Environment, **kwargs: Any):
        super().__init__(**kwargs)
        self.env = env

    def __call__(self, change: watchfiles.Change, path: str) -> bool:
        if self.env.is_uninteresting_source_name(os.path.basename(path)):
            return False
        return super().__call__(change, path)
