import os
import queue
import time
from collections import OrderedDict
from itertools import zip_longest

import click
from watchdog.events import DirModifiedEvent
from watchdog.events import FileMovedEvent
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer
from watchdog.observers.polling import PollingObserver

from lektor.utils import get_cache_dir


class EventHandler(FileSystemEventHandler):
    def __init__(self):
        super().__init__()
        self.queue = queue.Queue()

    def on_any_event(self, event):
        if not isinstance(event, DirModifiedEvent):
            if isinstance(event, FileMovedEvent):
                path = event.dest_path
            else:
                path = event.src_path
            self.queue.put((time.time(), event.event_type, path))


def _fullname(cls):
    """Return the full name of a class (including the module name)."""
    return f"{cls.__module__}.{cls.__qualname__}"


def _unique_everseen(seq):
    """Return the unique elements in sequence, preserving order."""
    return OrderedDict.fromkeys(seq).keys()


class BasicWatcher:
    def __init__(self, paths, observer_classes=(Observer, PollingObserver)):
        self.event_handler = EventHandler()
        self.paths = paths
        self.observer_classes = observer_classes
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
        observer = observer_class()
        for path in self.paths:
            observer.schedule(self.event_handler, path, recursive=True)
        observer.daemon = True
        observer.start()
        self.observer = observer

    def is_interesting(self, time, event_type, path):
        # pylint: disable=no-self-use
        return True

    def __iter__(self):
        while 1:
            time_, event_type, path = self.event_handler.queue.get()
            if self.is_interesting(time_, event_type, path):
                yield time_, event_type, path


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
    with Watcher(env) as watcher:
        try:
            for event in watcher:
                yield event
        except KeyboardInterrupt:
            pass
