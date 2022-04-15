import queue
import secrets

from flask import Blueprint, render_template, url_for

from lektor.admin.utils import eventstream
from lektor.reporter import ChangeStreamReporter

PING_DELAY = 1.0

bp = Blueprint("livereload", __name__)
# Use a random ID to detect reloading, which will be changed after reloaded
version_id = secrets.token_urlsafe(16)


@bp.route("/events")
@eventstream
def events():
    with ChangeStreamReporter(None) as reporter:
        while True:
            yield {"type": "ping", "versionId": version_id}

            try:
                artifact = reporter.next_change(PING_DELAY)
            except queue.Empty:
                continue
            yield {"type": "reload", "path": artifact.artifact_name}


@bp.route("/events/worker.js")
def worker_script():
    return (
        render_template("livereload-worker.js", events_url=url_for(".events")),
        200,
        {"Content-Type": "text/javascript"},
    )
