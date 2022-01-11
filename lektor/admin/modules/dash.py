from typing import Any

from flask import Blueprint
from flask import render_template
from flask import Response


bp = Blueprint("dash", __name__, url_prefix="/admin")


@bp.route("/<view>", endpoint="app")
def app_view(**kwargs: Any) -> Response:
    """Render the React admin GUI app."""
    return render_template("dash.html")
