import mimetypes
import os
from io import BytesIO
from zlib import adler32

from flask import abort
from flask import Blueprint
from flask import current_app
from flask import render_template
from flask import request
from flask import Response
from flask import url_for
from werkzeug.exceptions import NotFound
from werkzeug.wsgi import wrap_file

from lektor.constants import PRIMARY_ALT

bp = Blueprint("serve", __name__)


def rewrite_html_for_editing(fp, edit_url):
    button_script = render_template("edit-button.html", edit_url=edit_url)
    contents = fp.read()
    fp.close()
    head_endpos = contents.find(b"</head>")
    if head_endpos < 0:
        head_endpos = len(contents)
    return BytesIO(
        contents[:head_endpos] + button_script.encode("utf-8") + contents[head_endpos:]
    )


def send_file(fp, mimetype):
    try:
        fileno = fp.fileno()
        stat = os.stat(fileno)
    except OSError:
        stat = None

    resp = Response(
        wrap_file(request.environ, fp),
        mimetype=mimetype,
        direct_passthrough=True,
    )
    resp.cache_control.no_store = True
    if stat is not None:
        resp.cache_control.public = True
        resp.content_length = stat.st_size
        check = adler32(f"{stat.st_dev}:{stat.st_ino}".encode("ascii")) & 0xFFFFFFFF
        resp.set_etag(f"lektor-{stat.st_mtime}-{stat.st_size}-{check}")
    return resp


def handle_build_failure(failure):
    return render_template("build-failure.html", **failure.data)


def serve_up_artifact(path):
    li = current_app.lektor_info
    pad = li.get_pad()

    resolved = li.resolve_artifact("/" + path, pad)
    if resolved.filename is None:
        abort(404)

    artifact_name = resolved.artifact_name
    if artifact_name is None:
        artifact_name = path.strip("/")

    # If there was a build failure for the given artifact, we want
    # to render this instead of sending the (most likely missing or
    # corrupted) file.
    ctrl = li.get_failure_controller(pad)
    failure = ctrl.lookup_failure(artifact_name)
    if failure is not None:
        return handle_build_failure(failure)

    mimetype = mimetypes.guess_type(resolved.filename)[0]
    if mimetype is None:
        mimetype = "application/octet-stream"

    try:
        # pylint: disable=consider-using-with
        fp = open(resolved.filename, "rb")
    except OSError:
        abort(404)

    if mimetype == "text/html" and resolved.record_path is not None:
        assert "@" not in resolved.record_path
        alt = resolved.alt
        if not alt or alt in (PRIMARY_ALT, pad.db.config.primary_alternative):
            alt = None
        edit_url = url_for("dash.app", view="edit", path=resolved.record_path, alt=alt)
        fp = rewrite_html_for_editing(fp, edit_url)

    return send_file(fp, mimetype)


@bp.route("/", defaults={"path": ""})
@bp.route("/<path:path>")
def serve_artifact(path):
    return serve_up_artifact(path)


@bp.errorhandler(404)
def serve_error_page(error):
    try:
        return serve_up_artifact("404.html")
    except NotFound as e:
        return e
