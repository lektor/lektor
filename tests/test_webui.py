import flask
import pytest
from werkzeug.exceptions import HTTPException

from lektor.admin.webui import WebAdmin
from lektor.constants import PRIMARY_ALT


app = flask.Flask(__name__)


@pytest.fixture
def output_path(tmp_path):
    output_path = tmp_path / "webadmin"
    output_path.mkdir()
    return output_path


@pytest.fixture
def lektor_info(env, output_path):
    webadmin = WebAdmin(env, output_path=output_path.__fspath__())
    return webadmin.lektor_info


@pytest.fixture
def resolve_artifact(lektor_info):
    def resolve(url_path):
        with app.test_request_context(url_path):
            return lektor_info.resolve_artifact(url_path)

    return resolve


@pytest.mark.parametrize(
    "url_path, expected",
    [
        (
            "/dir_with_index_html/",
            (
                "dir_with_index_html/index.html",
                "dir_with_index_html/index.html",
                None,
                PRIMARY_ALT,
            ),
        ),
        (
            "/dir_with_index_htm/",
            (
                "dir_with_index_htm/index.htm",
                "dir_with_index_htm/index.htm",
                None,
                PRIMARY_ALT,
            ),
        ),
        (
            "/empty",
            # Resolves to Directory, so has alt
            (None, "empty", None, PRIMARY_ALT),
        ),
        ("/missing", (None, "missing", None, None)),  # Does not resolve, no alt
        ("/extra/", ("extra/index.html", "extra/index.html", "/extra", "en")),
        (
            "/de/extra/long/path/",
            (
                "de/extra/long/path/index.html",
                "de/extra/long/path/index.html",
                "/extra/slash-slug",
                "de",
            ),
        ),
    ],
)
def test_resolve_artifact(resolve_artifact, url_path, expected, output_path):
    def massage_expected(expected):
        artifact_name, filename, record_path, alt = expected
        # NB: this converts filename to native (e.g. pathsep=='\\' on windows) path
        filename = output_path.joinpath(filename).__fspath__()
        return artifact_name, filename, record_path, alt

    assert resolve_artifact(url_path) == massage_expected(expected)


@pytest.mark.parametrize(
    "url_path, location",
    [
        ("/dir_with_index_html", "dir_with_index_html/"),
        ("/dir_with_index_htm", "dir_with_index_htm/"),
    ],
)
def test_resolve_artifact_redirects(resolve_artifact, url_path, location):
    with pytest.raises(HTTPException) as exc:
        resolve_artifact(url_path)
    # add_slash_redirect in werkzeug>=2.1.0 returns 308 - previously it returned 301
    assert exc.value.response.status_code in (301, 308)
    assert exc.value.response.headers["Location"] == location
