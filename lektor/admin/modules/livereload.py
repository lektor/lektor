import json
import secrets
import threading
from typing import Any

from flask import Blueprint

from lektor.admin.utils import eventstream

PING_DELAY = 1.0

bp = Blueprint("livereload", __name__, static_folder="static")
# Use a random ID to detect reloading, which will be changed after reloaded
version_id = secrets.token_urlsafe(16)

reload_event = threading.Event()


def trigger_reload():
    """Trigger reload after a debounce delay."""
    reload_event.set()


def message(type_: str, **kwargs: Any) -> bytes:
    """
    Encode an event stream message.

    We distinguish message types with a 'type' inside the 'data' field, rather
    than the 'message' field, to allow the worker to process all messages with
    a single event listener.
    """
    jsonified = json.dumps({"type": type_, **kwargs})
    return f"data: {jsonified}\n\n".encode()


@bp.route("/events")
@eventstream
def events():
    while True:
        yield {"type": "ping", "versionId": version_id}

        should_reload = reload_event.wait(timeout=PING_DELAY)
        if should_reload:
            yield {"type": "reload"}
            reload_event.clear()
