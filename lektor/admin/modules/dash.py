from flask import Blueprint
from flask import current_app
from flask import render_template
from flask import request


bp = Blueprint("dash", __name__, url_prefix="/admin")


@bp.route("/<any(edit, delete, preview, add-child, upload):view>", endpoint="app")
def app_view(**kwargs):
    """Render the React admin GUI app."""
    return render_template(
        "dash.html",
        lektor_config={
            "admin_root": request.root_path,
            "site_root": request.environ["lektor.site_root"],
            "lang": current_app.config.get("lektor.ui_lang", "en"),
        },
    )
