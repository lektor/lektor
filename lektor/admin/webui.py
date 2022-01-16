import os
from typing import Any
from typing import NamedTuple
from typing import Optional
from typing import Sequence
from typing import Union

from flask import Flask
from flask import request
from werkzeug.utils import cached_property
from werkzeug.wsgi import pop_path_info

from lektor.admin.modules import api
from lektor.admin.modules import dash
from lektor.admin.modules import serve
from lektor.builder import Builder
from lektor.buildfailures import FailureController
from lektor.db import Database
from lektor.db import Pad
from lektor.db import Tree
from lektor.environment import Config
from lektor.environment import Environment
from lektor.reporter import CliReporter


class LektorInfo(NamedTuple):
    env: Environment
    output_path: Union[str, os.PathLike]
    verbosity: int = 0
    extra_flags: Optional[Sequence[str]] = None

    def make_lektor_context(self) -> "LektorContext":
        return LektorContext._make(self)


class LektorContext(LektorInfo):
    """Per-request object which provides the interface to Lektor for the Flask app(s).

    This does not provide any logic.  It just provides access to the
    needed Lektor internals and instances.
    """

    @property
    def project_id(self) -> str:
        return self.env.project.id

    @cached_property
    def database(self) -> Database:
        return Database(self.env)

    @cached_property
    def pad(self) -> Pad:
        return self.database.new_pad()

    @cached_property
    def tree(self) -> Tree:
        return Tree(self.pad)

    @property
    def config(self) -> Config:
        return self.database.config

    @cached_property
    def builder(self) -> Builder:
        return Builder(self.pad, self.output_path, self.extra_flags)

    @cached_property
    def failure_controller(self) -> FailureController:
        return FailureController(self.pad, self.output_path)

    def cli_reporter(self) -> CliReporter:
        return CliReporter(self.env, verbosity=self.verbosity)


class LektorApp(Flask):
    def __init__(
        self,
        lektor_info: LektorInfo,
        debug: bool = False,
        ui_lang: str = "en",
        **kwargs: Any,
    ) -> None:
        Flask.__init__(self, "lektor.admin", **kwargs)
        self.lektor_info = lektor_info
        self.config["lektor.ui_lang"] = ui_lang
        self.debug = debug
        self.config["PROPAGATE_EXCEPTIONS"] = True


def make_app(
    env: Environment,
    debug: bool = False,
    output_path: Optional[Union[str, os.PathLike]] = None,
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
    def admin_view(path):
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
