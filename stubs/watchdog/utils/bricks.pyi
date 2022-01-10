import queue
from typing import Tuple

from watchdog.events import FileSystemEvent
from watchdog.observers.api import ObservedWatch

class SkipRepeatsQueue(queue.Queue[Tuple[FileSystemEvent, ObservedWatch]]): ...
