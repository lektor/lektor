from __future__ import annotations

import os
import threading
import time
from collections import OrderedDict
from contextlib import suppress
from itertools import zip_longest

import click
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer
from watchdog.observers.api import DEFAULT_OBSERVER_TIMEOUT
from watchdog.observers.polling import PollingObserver

from lektor.utils import get_cache_dir


class EventHandler(FileSystemEventHandler):
    def __init__(self, is_interesting):
        super().__init__()
        self.is_interesting = is_interesting
        self.event = threading.Event()

    def _check(self, path):
        if self.is_interesting(None, None, path):
            self.event.set()

    # Generally we only care about changes (modification, creation, deletion) to files
    # within the monitored tree. Changes in directories do not directly affect Lektor
    # output. So, in general, we ignore directory events.
    #
    # However, the "efficient" (i.e. non-polling) observers do not seem to generate
    # events for files contained in directories that are moved out of the watched tree.
    # The only events generated in that case are for the directory — generally a
    # DirDeletedEvent is generated — so we can't ignore those.
    #
    # (Moving/renaming a directory does not seem to reliably generate a DirMovedEvent,
    # but we might as well track those, too.)

    def on_created(self, event):
        if not event.is_directory:
            self._check(event.src_path)

    def on_deleted(self, event):
        self._check(event.src_path)

    def on_modified(self, event):
        if not event.is_directory:
            self._check(event.src_path)

    def on_moved(self, event):
        self._check(event.src_path)
        self._check(event.dest_path)


def _fullname(cls):
    """Return the full name of a class (including the module name)."""
    return f"{cls.__module__}.{cls.__qualname__}"


def _unique_everseen(seq):
    """Return the unique elements in sequence, preserving order."""
    return OrderedDict.fromkeys(seq).keys()


class BasicWatcher:
    def __init__(
        self,
        paths,
        observer_classes=(Observer, PollingObserver),
        observer_timeout=DEFAULT_OBSERVER_TIMEOUT,  # testing
    ):
        self.event_handler = EventHandler(self.is_interesting)
        self.paths = paths
        self.observer_classes = observer_classes
        self.observer_timeout = observer_timeout
        self.observer = None

    def start(self):
        # Remove duplicates since there is no point in trying a given
        # observer class more than once. (This also simplifies the logic
        # for presenting sensible warning messages about broken
        # observers.)
        observer_classes = list(_unique_everseen(self.observer_classes))
        for observer_class, next_observer_class in zip_longest(
            observer_classes, observer_classes[1:]
        ):
            try:
                self._start_observer(observer_class)
                return
            except Exception as exc:
                if next_observer_class is None:
                    raise
                click.secho(
                    f"Creation of {_fullname(observer_class)} failed with exception:\n"
                    f"  {exc.__class__.__name__}: {exc!s}\n"
                    "This may be due to a configuration or other issue with your system.\n"
                    f"Falling back to {_fullname(next_observer_class)}.",
                    fg="red",
                    bold=True,
                )

    def stop(self):
        self.observer.stop()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, ex_type, ex_value, ex_tb):
        self.stop()

    def _start_observer(self, observer_class=Observer):
        if self.observer is not None:
            raise RuntimeError("Watcher already started.")
        observer = observer_class(timeout=self.observer_timeout)
        for path in self.paths:
            observer.schedule(self.event_handler, path, recursive=True)
        observer.daemon = True
        observer.start()
        self.observer = observer

    def is_interesting(self, time, event_type, path):
        # pylint: disable=no-self-use
        return True

    @property
    def event(self):
        return self.event_handler.event

    def wait(self, timeout: float | None = None):
        """Wait for watched filesystem change.

        This waits for a “new” non-ignored filesystem change.  Here “new” means that
        the change happened since the last return from ``wait``.

        Waits a maximum of ``timeout`` seconds (or forever if ``timeout`` is ``None``).

        Returns ``True`` if a change occurred, ``False`` on timeout.
        """
        if not self.event.wait(timeout=timeout):
            return False
        self.event.clear()
        return True


class Watcher(BasicWatcher):
    def __init__(self, env, output_path=None):
        BasicWatcher.__init__(self, paths=[env.root_path] + env.theme_paths)
        self.env = env
        self.output_path = output_path
        self.cache_dir = os.path.abspath(get_cache_dir())

    def is_interesting(self, time, event_type, path):
        path = os.path.abspath(path)

        if self.env.is_uninteresting_source_name(os.path.basename(path)):
            return False
        if path.startswith(self.cache_dir):
            return False
        if self.output_path is not None and path.startswith(
            os.path.abspath(self.output_path)
        ):
            return False
        return True


def watch(env):
    """Returns a generator of file system events in the environment."""
    with Watcher(env) as watcher, suppress(KeyboardInterrupt):
        while True:
            watcher.wait()
            yield time.time(), None, None
