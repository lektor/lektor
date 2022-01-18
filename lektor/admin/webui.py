from typing import Optional
from typing import Sequence
from typing import TYPE_CHECKING
from typing import Union

from flask import request
from werkzeug.wsgi import pop_path_info

from lektor.admin.common import LektorApp
from lektor.admin.common import LektorInfo
from lektor.admin.modules import api
from lektor.admin.modules import dash
from lektor.admin.modules import serve
from lektor.environment import Environment

if TYPE_CHECKING:
    import os
    from typing import Any
    from _typeshed.wsgi import WSGIApplication


def make_app(
    env: Environment,
    debug: bool = False,
    output_path: Optional[Union[str, "os.PathLike[Any]"]] = None,
    ui_lang: str = "en",
    verbosity: int = 0,
    extra_flags: Optional[Sequence[str]] = None,
    *,
    admin_path: str = "/admin",
) -> LektorApp:
    if output_path is None:
        output_path = env.project.get_output_path()

    lektor_info = LektorInfo(env, output_path, verbosity, extra_flags)

    # The top-level app has a route that matches anything
    # ("/<path:path>" in the serve blueprint).  That means that if
    # there is another route whose doesn't match based on request
    # method, the serve view will take over and try to serve it.  To
    # prevent this from happening for the paths under /admin, we
    # structure them as a separate flask app.
    admin_app = LektorApp(lektor_info, debug=debug, ui_lang=ui_lang)
    admin_app.register_blueprint(dash.bp, url_prefix="/")
    admin_app.register_blueprint(api.bp, url_prefix="/api")

    app = LektorApp(lektor_info, debug=debug, static_url_path=f"{admin_path}/static")
    app.register_blueprint(serve.bp)

    # Pass requests for /admin/... to the admin app
    @app.route(f"{admin_path}/<path:path>", methods=["GET", "POST", "PUT"])
    def admin_view(path: str) -> "WSGIApplication":
        environ = request.environ
        # Save top-level SCRIPT_NAME (used by dash)
        environ["lektor.site_root"] = request.root_path
        while environ.get("PATH_INFO", "") != f"/{path}":
            assert environ["PATH_INFO"]
            pop_path_info(request.environ)
        return admin_app.wsgi_app

    # Add rule to construct URL to /admin/edit
    app.add_url_rule(f"{admin_path}/edit", "url.edit", build_only=True)

    return app


WebAdmin = WebUI = make_app
