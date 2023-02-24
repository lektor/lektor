import flask
import pytest

import lektor.admin.webui


@pytest.fixture
def output_path(tmp_path):
    output_path = tmp_path / "output_path"
    output_path.mkdir()
    return output_path


@pytest.fixture
def static_folder(tmp_path) -> str:
    scratch_folder = tmp_path / "static"
    scratch_folder.mkdir()
    return scratch_folder


@pytest.fixture
def test_client(env, static_folder, output_path):
    app = lektor.admin.webui.make_app(
        env, output_path=output_path, static_folder=static_folder
    )
    with app.test_client() as client:
        yield client


@pytest.fixture
def app_static_dummy_txt(static_folder):
    """Create a dummy file in the Flask apps static directory."""
    dummy_txt = static_folder / "dummy.txt"
    dummy_txt.touch()


################################################################


@pytest.mark.parametrize(
    "url, mimetype, is_editable",
    [
        ("/projects/coffee/", "text/html", True),  # Page
        ("/hello.txt", "text/plain", False),  # Attachment
        # Asset file
        ("/static/demo.css", "text/css", False),
        # Asset directories with index.{htm,html}
        ("/dir_with_index_html/", "text/html", False),
        ("/dir_with_index_htm/", "text/html", False),
        ("/dir_with_index_html/index.html", "text/html", False),
        ("/dir_with_index_htm/index.htm", "text/html", False),
        # Flask static directory
        ("/admin/static/dummy.txt", "text/plain", False),
    ],
)
@pytest.mark.usefixtures("app_static_dummy_txt")
def test_get(test_client, url, mimetype, is_editable):
    resp = test_client.get(url)
    assert resp.status_code == 200
    assert resp.mimetype == mimetype
    data = b"".join(resp.get_app_iter(flask.request.environ)).decode("utf-8")
    assert ("/admin/edit?" in data) == is_editable


def test_get_admin_does_something_useful(test_client, mocker):
    # Test that GET /admin eventually gets to the admin JS app
    # See https://github.com/lektor/lektor/issues/1043
    render_template = mocker.patch(
        "lektor.admin.modules.dash.render_template",
        return_value="RENDERED",
    )
    resp = test_client.get("/admin", follow_redirects=True)
    assert resp.status_code == 200
    assert resp.get_data(as_text=True) == render_template.return_value
    assert render_template.mock_calls == [
        mocker.call("dash.html", lektor_config=mocker.ANY),
    ]
