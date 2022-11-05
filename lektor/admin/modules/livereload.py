import queue
import secrets

from flask import Blueprint
from flask import render_template
from flask import url_for

from lektor.admin.utils import eventstream
from lektor.reporter import reporter

PING_DELAY = 1.0

bp = Blueprint("livereload", __name__)
# Use a random ID to detect reloading, which will be changed after reloaded
version_id = secrets.token_urlsafe(16)


@bp.route("/events")
@eventstream
def events():
    events = queue.Queue()
    with reporter.on_build_change(events.put):
        while True:
            yield {"type": "ping", "versionId": version_id}

            try:
                change = events.get(timeout=PING_DELAY)
            except queue.Empty:
                continue
            yield {"type": "reload", "path": change.artifact_name}


@bp.route("/events/worker.js")
def worker_script():
    return (
        render_template("livereload-worker.js", events_url=url_for(".events")),
        200,
        {"Content-Type": "text/javascript"},
    )
