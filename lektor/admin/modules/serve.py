import json
import mimetypes
import os
import string
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


_EDIT_BUTTON_STYLE = """
  <style type="text/css">
    #lektor-edit-link {
      position: fixed;
      z-index: 9999999;
      right: 10px;
      top: 10px;
      position: fixed;
      margin: 0;
      font-family: 'Verdana', sans-serif;
      background: #eee;
      color: #77304c;
      font-weight: normal;
      font-size: 32px;
      padding: 0;
      text-decoration: none!important;
      border: 1px solid #ccc!important;
      width: 40px;
      height: 40px;
      line-height: 40px;
      text-align: center;
      opacity: 0.7;
    }

    #lektor-edit-link:hover {
      background: white!important;
      opacity: 1.0;
      border: 1px solid #aaa!important;
    }
  </style>
"""


_EDIT_BUTTON_SCRIPT_TMPL = string.Template(
    """
  <script type="text/javascript">
    (function() {
      if (window != window.top) {
        return;
      }
      var link = document.createElement('a');
      link.setAttribute('href', ${edit_url});
      link.setAttribute('id', 'lektor-edit-link');
      link.innerHTML = '\u270E';
      document.body.appendChild(link);
    })();
  </script>
"""
)


def rewrite_html_for_editing(fp, edit_url):
    contents = fp.read()
    fp.close()
    head_endpos = contents.find(b"</head>")
    body_endpos = contents.find(b"</body>")
    if head_endpos < 0:
        # If </head> not found, inject both <style> and <script> at end
        head_endpos = body_endpos = len(contents)
    elif body_endpos < 0:
        # If </body> not found, inject <script> at end
        body_endpos = len(contents)

    button_script = _EDIT_BUTTON_SCRIPT_TMPL.substitute(
        edit_url=json.dumps(edit_url)
    ).encode("utf-8")

    return BytesIO(
        contents[:head_endpos]
        + _EDIT_BUTTON_STYLE.encode("utf-8")
        + contents[head_endpos:body_endpos]
        + button_script
        + contents[body_endpos:]
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
