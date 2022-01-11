import os
from typing import Optional

from flask import Blueprint
from flask import current_app
from flask import g
from flask import request
from werkzeug.utils import cached_property

from lektor.admin.webui import WebUI
from lektor.db import Pad
from lektor.db import Tree


bp = Blueprint("common", __name__)


class AdminContext:
    def __init__(self) -> None:
        assert isinstance(current_app, WebUI)
        url_prefix = current_app.blueprints["dash"].url_prefix or ""
        self.admin_root = url_prefix.rstrip("/")
        self.site_root = request.script_root
        self.info = current_app.lektor_info

    def get_temp_path(self, name: Optional[str] = None) -> str:
        if name is None:
            name = os.urandom(20).hex()
        dirname = self.info.env.temp_path
        try:
            os.makedirs(dirname)
        except OSError:
            pass
        return os.path.join(dirname, name)

    @cached_property
    def pad(self) -> Pad:
        assert isinstance(current_app, WebUI)
        return current_app.lektor_info.get_pad()

    @cached_property
    def tree(self) -> Tree:
        return Tree(self.pad)


@bp.before_app_request
def find_common_info() -> None:
    # pylint: disable=assigning-non-slot
    g.admin_context = AdminContext()
