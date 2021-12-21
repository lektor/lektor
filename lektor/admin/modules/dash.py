from flask import abort
from flask import Blueprint
from flask import g
from flask import redirect
from flask import render_template
from flask import request
from flask import url_for
from werkzeug.wsgi import extract_path_info

from lektor.constants import PRIMARY_ALT


bp = Blueprint("dash", __name__, url_prefix="/admin")


@bp.route("/edit")
def edit_redirect():
    record = None

    # Find out where we wanted to go to.  We need to chop off the leading
    # /admin on this URL as this is where the admin thinks it's placed.
    path = extract_path_info(
        request.url_root.rstrip("/").rsplit("/", 1)[0], request.args.get("path", "/")
    )

    if path is not None:
        record = g.admin_context.pad.resolve_url_path(path, alt_fallback=False)
    if record is None:
        abort(404)
    path, _, _ = record.path.lstrip("/").partition("@")
    alt = record.alt
    if alt == PRIMARY_ALT:
        alt = None

    return redirect(url_for("dash.app", path=path, alt=alt, view="edit"))


# This first path is only use to construct the AdminContext.admin_root.
# If one actually visits the URL, the React app immediately redirects to
# one of the subsequent two paths.
@bp.route("/", endpoint="app", defaults={"path": "/", "view": "edit"})
@bp.route("/<view>/", endpoint="app", defaults={"path": ""})
@bp.route("/<view>/<path:path>", endpoint="app")
def app_view(**kwargs):
    """Render the React admin GUI app."""
    return render_template("dash.html")
