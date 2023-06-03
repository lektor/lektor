from __future__ import annotations

import queue
import secrets
from typing import Generator
from typing import TYPE_CHECKING

from flask import Blueprint
from flask import render_template
from flask import url_for

from lektor.admin.utils import eventstream
from lektor.reporter import reporter

if TYPE_CHECKING:
    from flask.typing import ResponseReturnValue
    from lektor.builder import Artifact

PING_DELAY = 1.0

bp = Blueprint("livereload", __name__)
# Use a random ID to detect reloading, which will be changed after reloaded
version_id = secrets.token_urlsafe(16)


@bp.route("/events")
@eventstream
def events() -> Generator[dict[str, str], None, None]:
    updated_artifacts: queue.Queue[Artifact] = queue.Queue()
    with reporter.on_build_change(updated_artifacts.put):
        while True:
            yield {"type": "ping", "versionId": version_id}

            try:
                artifact = updated_artifacts.get(timeout=PING_DELAY)
            except queue.Empty:
                continue
            yield {"type": "reload", "path": artifact.artifact_name}


@bp.route("/events/worker.js")
def worker_script() -> ResponseReturnValue:
    return (
        render_template("livereload-worker.js", events_url=url_for(".events")),
        200,
        {"Content-Type": "text/javascript"},
    )
