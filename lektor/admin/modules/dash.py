from flask import Blueprint
from flask import render_template


bp = Blueprint("dash", __name__, url_prefix="/admin")


# This first path is only use to construct the AdminContext.admin_root.
# If one actually visits the URL, the React app immediately redirects to
# one of the subsequent two paths.
@bp.route("/", endpoint="app", defaults={"path": "/", "view": "edit"})
@bp.route("/<view>/", endpoint="app", defaults={"path": ""})
@bp.route("/<view>/<path:path>", endpoint="app")
def app_view(**kwargs):
    """Render the React admin GUI app."""
    return render_template("dash.html")
