import json
import secrets
import threading
from typing import Any, Generator, Optional

from flask import Blueprint, current_app, request
from werkzeug.exceptions import NotAcceptable

PING_DELAY = 1.0
RELOAD_DEBOUNCE_TIME = 0.05  # seconds

bp = Blueprint("livereload", __name__, static_folder="static")
# Use a random ID to detect reloading, which will be changed after reloaded
version_id = secrets.token_urlsafe(16)

reload_event = threading.Event()
reload_timer: Optional[threading.Timer] = None


def trigger_reload():
    """Trigger reload after a debounce delay."""
    global reload_timer
    if reload_timer is not None:
        reload_timer.cancel()

    reload_timer = threading.Timer(RELOAD_DEBOUNCE_TIME, reload_event.set)
    reload_timer.start()


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
def events():
    if "text/event-stream" not in request.accept_mimetypes:
        raise NotAcceptable()

    def event_stream() -> Generator[bytes, None, None]:
        while True:
            yield message("ping", versionId=version_id)

            should_reload = reload_event.wait(timeout=PING_DELAY)
            if should_reload:
                reload_event.clear()
                yield message("reload")

    return current_app.response_class(event_stream(), mimetype="text/event-stream")
