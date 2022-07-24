from wsgiref.util import shift_path_info

import pytest
from werkzeug.exceptions import NotFound
from werkzeug.test import Client

from lektor.admin.webui import make_app


@pytest.fixture
def app(env, ui_lang, tmp_path, admin_path, app_prefix):
    app = make_app(env, output_path=tmp_path, ui_lang=ui_lang, admin_path=admin_path)
    if not app_prefix:
        return app

    def prefixed_app(environ, start_response):
        if shift_path_info(environ) != app_prefix:
            return NotFound()(environ, start_response)
        return app(environ, start_response)

    return prefixed_app


@pytest.mark.parametrize("ui_lang", ["en", "de"])
@pytest.mark.parametrize("admin_path", ["/_admin"])
@pytest.mark.parametrize("app_prefix", [None, "prefix"])
def test_dash(app, ui_lang, mocker, admin_path, app_prefix):
    render_template = mocker.patch(
        "lektor.admin.modules.dash.render_template",
        return_value="RENDERED",
    )
    script_name = f"/{app_prefix}" if app_prefix else ""

    resp = Client(app).get(f"{script_name}{admin_path}/edit?path=%2F")

    assert resp.get_data(True) == "RENDERED"
    assert render_template.mock_calls == [
        mocker.call(
            "dash.html",
            lektor_config={
                "admin_root": script_name + admin_path,
                "site_root": script_name,
                "lang": ui_lang,
            },
        )
    ]
