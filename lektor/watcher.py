import os
import time

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, DirModifiedEvent, FileMovedEvent

from lektor._compat import queue
from lektor.utils import get_cache_dir

# Alias this as this can be called during interpreter shutdown
_Empty = queue.Empty


class EventHandler(FileSystemEventHandler):

    def __init__(self, callback=None):
        if callback is not None:
            self.queue = None
            self.callback = callback
        else:
            self.queue = queue.Queue()
            self.callback = self.queue.put

    def on_any_event(self, event):
        if not isinstance(event, DirModifiedEvent):
            path = event.dest_path if isinstance(event, FileMovedEvent) else event.src_path
            item = (time.time(), event.event_type, path)
            if self.queue is not None:
                self.queue.put(item)
            else:
                self.callback(*item)


class BasicWatcher(object):

    def __init__(self, paths, callback=None):
        self.event_handler = EventHandler(callback=callback)
        self.observer = Observer()
        for path in paths:
            self.observer.schedule(self.event_handler, path, recursive=True)
        self.observer.setDaemon(True)

    def is_interesting(self, time, event_type, path):
        return True

    def __iter__(self):
        if self.event_handler.queue is None:
            raise RuntimeError('watcher used with callback')
        while 1:
            try:
                item = self.event_handler.queue.get(timeout=1)
                if self.is_interesting(*item):
                    yield item
            except _Empty:
                pass


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
        if self.output_path is not None and path.startswith(os.path.abspath(self.output_path)):
            return False
        return True


def watch(env):
    """Returns a generator of file system events in the environment."""
    watcher = Watcher(env)
    watcher.observer.start()
    try:
        for event in watcher:
            yield event
    except KeyboardInterrupt:
        watcher.observer.stop()
