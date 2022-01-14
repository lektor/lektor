import os
from typing import Any
from typing import Callable
from typing import Iterator
from numbers import Real

from watchdog.observers.api import (
    BaseObserver,
    EventQueue,
    EventEmitter,
    ObservedWatch,
)

class PollingEmitter(EventEmitter):
    def __init__(
        self,
        event_queue: EventQueue,
        watch: ObservedWatch,
        timeout: Real = ...,
        stat: Callable[..., os.stat_result] = ...,
        listdir: Callable[..., Iterator[Any]] = ...,
    ) -> None: ...
    def on_thread_start(self) -> None: ...
    def queue_events(self, timeout: Real) -> None: ...

class PollingObserver(BaseObserver):
    def __init__(self, timeout: Real = ...) -> None: ...

class PollingObserverVFS(BaseObserver):
    def __init__(
        self,
        stat: Callable[..., os.stat_result],
        listdir: Callable[..., Iterator[Any]],
        polling_interval: Real = ...,
    ) -> None: ...
