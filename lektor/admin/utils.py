from collections.abc import Iterable
from collections.abc import Iterator
from functools import update_wrapper
from itertools import chain
from typing import Any
from typing import Callable

from flask import json
from flask import Response


def eventstream(f: Callable[..., Iterable[Any]]) -> Callable[..., Response]:
    def new_func(*args: Any, **kwargs: Any) -> Response:
        def generate() -> Iterator[bytes]:
            for event in chain(f(*args, **kwargs), (None,)):
                yield f"data: {json.dumps(event)}\n\n".encode()

        return Response(
            generate(), mimetype="text/event-stream", direct_passthrough=True
        )

    return update_wrapper(new_func, f)
