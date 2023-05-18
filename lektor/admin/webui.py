from __future__ import annotations

from typing import TYPE_CHECKING
from wsgiref.util import shift_path_info

from flask import Flask
from flask import request

from lektor.admin.context import LektorApp
from lektor.admin.context import LektorInfo
from lektor.admin.modules import api
from lektor.admin.modules import dash
from lektor.admin.modules import livereload
from lektor.admin.modules import serve
from lektor.environment import Environment

if TYPE_CHECKING:
    from _typeshed import StrPath
    from _typeshed.wsgi import WSGIApplication


def _common_configuration(app: Flask, debug: bool = False) -> None:
    app.debug = debug
    app.config["PROPAGATE_EXCEPTIONS"] = True


def make_app(
    env: Environment,
    debug: bool = False,
    output_path: StrPath | None = None,
    ui_lang: str = "en",
    verbosity: int = 0,
    extra_flags: dict[str, str] | None = None,
    reload: bool = True,
    *,
    admin_path: str = "/admin",
    static_folder: StrPath | None = "static",  # testing
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
    admin_app = LektorApp(lektor_info)
    _common_configuration(admin_app, debug=debug)
    admin_app.config["lektor.ui_lang"] = ui_lang
    admin_app.register_blueprint(dash.bp, url_prefix="/")
    admin_app.register_blueprint(api.bp, url_prefix="/api")

    # Serve static files from top-level app
    app = LektorApp(
        lektor_info, static_url_path=f"{admin_path}/static", static_folder=static_folder
    )
    _common_configuration(app, debug=debug)
    app.config["ENABLE_LIVERELOAD"] = reload
    if reload:
        app.register_blueprint(livereload.bp, url_prefix="/__reload__")
    app.register_blueprint(serve.bp)

    # Pass requests for /admin/... to the admin app
    @app.route(f"{admin_path}/", defaults={"page": ""})
    @app.route(f"{admin_path}/<path:page>", methods=["GET", "POST", "PUT"])
    def admin_view(page: str) -> "WSGIApplication":
        environ = request.environ
        # Save top-level SCRIPT_NAME (used by dash)
        environ["lektor.site_root"] = request.root_path
        while environ.get("PATH_INFO", "") != f"/{page}":
            assert environ["PATH_INFO"]
            shift_path_info(request.environ)
        return admin_app.wsgi_app

    # Add rule to construct URL to /admin/edit
    app.add_url_rule(f"{admin_path}/edit", "url.edit", build_only=True)

    return app


WebAdmin = WebUI = make_app
