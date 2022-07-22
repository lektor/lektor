import inspect
import os
import shutil
import sys
from pathlib import Path
from urllib.parse import parse_qsl
from urllib.parse import urljoin
from urllib.parse import urlparse

import flask
import pytest
from werkzeug.exceptions import NotFound

from lektor.admin.context import LektorContext
from lektor.admin.modules import serve
from lektor.admin.webui import LektorApp
from lektor.admin.webui import LektorInfo
from lektor.assets import Asset
from lektor.buildfailures import FailureController
from lektor.db import Record
from lektor.environment import Environment
from lektor.project import Project


@pytest.fixture(scope="session")
def dummy_app():
    return flask.Flask("lektor.admin")


@pytest.fixture
def dummy_app_context(dummy_app):
    with dummy_app.app_context():
        yield


@pytest.mark.parametrize(
    "html_text, expect_at_tail",
    [
        ("<html><head></head><body></body></html>", False),
        ("<html>\n<head>\n  </head>\n<body>\n</body>\n</html>", False),
        ("<html><head></ head  ><body></body></html>", False),
        ("<html><head></HeAd><body></body></html>", False),
        ("<html></html>", True),
        ("<html><header></header><body></body></html>", True),
    ],
)
@pytest.mark.usefixtures("dummy_app_context")
def test_rewrite_html_for_editing(html_text, expect_at_tail):
    eof_mark = "---EOF---"
    edit_url = "http://example.com/EDIT_URL"
    rewritten = serve._rewrite_html_for_editing(
        f"{html_text}{eof_mark}".encode("utf-8"), edit_url
    )
    html, _, tail = rewritten.decode("utf-8").rpartition(eof_mark)
    if expect_at_tail:
        assert edit_url in tail
        assert edit_url not in html
    else:
        assert edit_url not in tail
        assert edit_url in html


@pytest.mark.usefixtures("dummy_app_context")
def test_send_html_for_editing(tmp_path):
    html_file = tmp_path / "test.html"
    html_file.write_text("<html><head></head><body></body></html>")
    resp = serve._send_html_for_editing(html_file, "EDIT_URL")
    assert resp.mimetype == "text/html"
    # pylint: disable=unsupported-membership-test
    assert "EDIT_URL" in resp.get_data(True)


@pytest.mark.usefixtures("dummy_app_context")
def test_send_html_for_editing_etag_depends_on_edit_url(tmp_path):
    html_file = tmp_path / "test.html"
    html_file.write_text("<html><head></head><body></body></html>")
    resp1 = serve._send_html_for_editing(html_file, "EDIT_URL1")
    resp2 = serve._send_html_for_editing(html_file, "EDIT_URL2")
    assert resp2.headers["ETag"] != resp1.headers["ETag"]
    resp3 = serve._send_html_for_editing(html_file, "EDIT_URL1")
    assert resp3.headers["ETag"] == resp1.headers["ETag"]


def test_send_html_for_editing_raises_404(tmp_path):
    with pytest.raises(NotFound):
        serve._send_html_for_editing(tmp_path / "missing.html", "EDIT_URL")


@pytest.mark.parametrize(
    "filename, mimetype",
    [
        ("junk.html", "text/html"),
        ("test.HTM", "text/html"),
        ("test.txt", "text/plain"),
        ("test.foo", "application/octet-stream"),
    ],
)
def test_deduce_mimetype(filename, mimetype):
    assert serve._deduce_mimetype(filename) == mimetype


def test_checked_send_file(tmp_path, dummy_app):
    filename = tmp_path / "file"
    filename.write_text("content")

    with dummy_app.test_request_context():
        resp = serve._checked_send_file(filename, "image/png")
    assert resp.headers["Content-Type"] == "image/png"


def test_checked_send_file_raises_404(tmp_path, dummy_app):
    with dummy_app.test_request_context():
        with pytest.raises(NotFound):
            serve._checked_send_file(tmp_path / "missing.txt", "text/plain")


################################################################


def write_text(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(inspect.cleandoc(text))


@pytest.fixture(scope="module")
def project_path(tmp_path_factory, data_path):
    """Make our own private copy of the demo-project"""
    demo = data_path / "demo-project"
    path = tmp_path_factory.mktemp("test_serve") / "demo-project"

    shutil.copytree(demo, path)

    # Add a page which will fail to build
    write_text(
        path / "content/extra/build-failure/contents.lr",
        """
        _model: page
        ---
        title: Build Failure
        ---
        _template: missing.html
        """,
    )
    # Add a page which will build to a *.txt file
    write_text(
        path / "content/extra/test.txt/contents.lr",
        """
        _model: page
        ---
        title: Text File
        """,
    )
    return path


@pytest.fixture
def output_path(tmp_path):
    output_path = tmp_path / "output_path"
    output_path.mkdir()
    return output_path


@pytest.fixture(params=[None, ["FLAG"]])
def flag(request):
    return request.param


@pytest.fixture
def app(output_path, project_path, flag):
    project = Project.from_path(project_path)
    env = Environment(project, load_plugins=False)
    lektor_info = LektorInfo(env, output_path, extra_flags=flag)
    app = LektorApp(lektor_info)
    app.register_blueprint(serve.bp, url_prefix="/")
    app.add_url_rule("/ADMIN/EDIT", "url.edit", build_only=True)
    return app


################################################################


class TestArtifactServer:
    # pylint: disable=no-self-use

    @pytest.fixture
    def a_s(self, app):
        lektor_context = LektorContext._make(app.lektor_info)
        return serve.ArtifactServer(lektor_context)

    @pytest.fixture
    def pad(self, app):
        return app.lektor_info.env.new_pad()

    @pytest.fixture
    def failure_controller(self, pad, output_path):
        return FailureController(pad, output_path)

    @pytest.fixture
    def failed_artifact(self, mocker, failure_controller):
        artifact_name = "failed/index.html"
        try:
            raise RuntimeError("Failure")
        except Exception:
            failure_controller.store_failure(artifact_name, sys.exc_info())
        try:
            yield mocker.NonCallableMock(name="Artifact", artifact_name=artifact_name)
        finally:
            failure_controller.clear_failure(artifact_name)

    @pytest.mark.parametrize(
        "url_path, source_path",
        [
            ("", "/"),
            ("index.html", "/"),
            ("de/", "/"),
            ("de/index.html", "/"),
            ("extra/", "/extra"),
            ("extra/index.html", "/extra"),
            ("de/extra/", "/extra"),
            ("de/extra/index.html", "/extra"),
            ("extra/long/path/", "/extra/slash-slug"),
            ("blog", "/blog@1"),
            ("blog/2015/12/post1/", "/blog/post1"),
            ("de/blog/", "/blog@1"),
            ("extra/container", "/extra/container"),
        ],
    )
    def test_resolve_url_path(self, a_s, url_path, source_path):
        source = a_s.resolve_url_path(url_path)
        assert isinstance(source, Record)
        assert source.path == source_path

    @pytest.mark.parametrize(
        "url_path",
        [
            "static/demo.css",
            "dir_with_index_html/",
            "dir_with_index_htm/",
            "static/",
        ],
    )
    def test_resolve_url_path_to_asset(self, a_s, url_path, project_path):
        asset_path = project_path / "assets"
        source = a_s.resolve_url_path(url_path)
        assert isinstance(source, Asset)
        assert Path(source.source_filename) == asset_path / url_path

    @pytest.mark.parametrize(
        "url_path",
        [
            "missing",
            "dir_with_index_html/index.htm",
            "dir_with_index_htm/index.html",
            "static/index.html",
        ],
    )
    def test_resolve_url_path_raises_404(self, a_s, url_path):
        with pytest.raises(NotFound):
            a_s.resolve_url_path(url_path)

    @pytest.mark.parametrize(
        "dir_name, index_name",
        [
            ("dir_with_index_html", "index.html"),
            ("dir_with_index_htm", "index.htm"),
        ],
    )
    def test_resolve_directory_index(self, a_s, pad, dir_name, index_name):
        directory = pad.asset_root.get_child(dir_name)
        index = a_s.resolve_directory_index(directory)
        assert index.name == index_name

    def test_resolve_directory_index_raises_404(self, a_s, pad):
        directory = pad.asset_root.get_child("static")
        with pytest.raises(NotFound):
            a_s.resolve_directory_index(directory)

    @pytest.mark.parametrize(
        "url_path, artifact_name, failing",
        [
            ("de/extra/", "de/extra/index.html", False),
            ("dir_with_index_html/", None, False),
            ("dir_with_index_htm/", None, False),
            ("dir_with_index_html/index.html", "dir_with_index_html/index.html", False),
            ("dir_with_index_htm/index.htm", "dir_with_index_htm/index.htm", False),
            ("static/", None, False),
            ("/extra/build-failure", "extra/build-failure/index.html", True),
            ("/extra/file.ext", "extra/file.ext", False),
        ],
    )
    def test_build_primary_artifact(self, a_s, url_path, artifact_name, failing):
        source = a_s.resolve_url_path(url_path)
        assert source is not None
        if artifact_name is None:
            with pytest.raises(NotFound):
                a_s.build_primary_artifact(source)
        else:
            artifact, failure = a_s.build_primary_artifact(source)
            assert artifact.artifact_name == artifact_name
            assert (failure is not None) == failing

    def test_build_primary_artifact_raises_404(self, a_s, pad):
        source = pad.get("/extra/container")  # has _hidden = yes
        assert source is not None
        with pytest.raises(NotFound):
            a_s.build_primary_artifact(source)

    @pytest.mark.parametrize("edit_url", [None, "EDIT_URL"])
    def test_handle_build_failure(self, app, a_s, mocker, edit_url):
        failure = mocker.NonCallableMock(
            name="BuildFailure",
            data={k: k.upper() for k in ("artifact", "exception", "traceback")},
        )
        with app.test_request_context("failing/"):
            resp = a_s.handle_build_failure(failure, edit_url)
        assert resp.status_code == 200
        assert "TRACEBACK" in resp.get_data(True)
        if edit_url is not None:
            assert edit_url in resp.get_data(True)

    @pytest.mark.parametrize(
        "path, kw, expect",
        [
            ("/blog", {"page_num": 1}, {("path", "/blog")}),
            ("/extra", {"alt": "de"}, {("path", "/extra"), ("alt", "de")}),
            ("/extra", {"alt": "en"}, {("path", "/extra")}),
        ],
    )
    def test_get_edit_url(self, a_s, app, pad, path, kw, expect):
        source = pad.get(path, **kw)
        with app.test_request_context(path):
            edit_url = a_s.get_edit_url(source)
        if expect is None:
            assert edit_url is None
        else:
            url = urlparse(edit_url)
            assert url.path == "/ADMIN/EDIT"
            assert set(parse_qsl(url.query)) == expect

    @pytest.mark.parametrize(
        "url_path, location",
        [
            ("extra", "extra/"),
            ("dir_with_index_html", "dir_with_index_html/"),
        ],
    )
    def test_serve_artifact_adds_slash(self, a_s, app, url_path, location):
        with app.test_request_context(f"/{url_path}"):
            resp = a_s.serve_artifact(url_path)
        assert resp.status_code in (301, 308)
        assert resp.location == location

    @pytest.mark.parametrize(
        "url_path, mimetype, is_editable",
        [
            ("projects/coffee/", "text/html", True),  # Page
            ("extra/test.txt", "text/plain", False),  # non-HTML Page
            ("hello.txt", "text/plain", False),  # Attachment
            # Check that build-failure report has edit pencil
            ("extra/build-failure/", "text/html", True),  # Failing build
            # Asset file
            ("static/demo.css", "text/css", False),
            # Page with hidden parent
            ("extra/container/a/", "text/html", True),
            # Asset file with hidden parent
            ("extra/container/hello.txt", "text/plain", False),
            # Asset directories with index.{htm,html}
            ("dir_with_index_html/", "text/html", False),
            ("dir_with_index_htm/", "text/html", False),
            ("dir_with_index_html/index.html", "text/html", False),
            ("dir_with_index_htm/index.htm", "text/html", False),
        ],
    )
    def test_serve_artifact_serves_artifact(
        self, a_s, app, url_path, mimetype, is_editable
    ):
        with app.test_request_context(f"/{url_path}"):
            resp = a_s.serve_artifact(url_path)
            assert resp.status_code == 200
            assert resp.mimetype == mimetype
            data = b"".join(resp.get_app_iter(flask.request.environ)).decode("utf-8")
        assert ("/ADMIN/EDIT?" in data) == is_editable

    @pytest.mark.parametrize(
        "url_path",
        [
            "test@192.jpg",  # sub-artifact — no resolvable to source object
            "extra/container/",  # hidden page
            "static/",  # Asset directory without index.html
            "dir_with_index_html/index.htm",
            "dir_with_index_htm/index.html",
        ],
    )
    def test_serve_artifact_raises_404(self, a_s, app, url_path):
        with app.test_request_context(f"/{url_path}"):
            with pytest.raises(NotFound):
                a_s.serve_artifact(url_path)


################################################################


def test_serve_artifact(app):
    with app.test_request_context("/static/demo.css"):
        resp = serve.serve_artifact("static/demo.css")
        assert resp.status_code == 200
        assert resp.mimetype == "text/css"


def test_serve_file(output_path, app):
    filename = output_path / "test.txt"
    filename.write_text("content")
    with app.test_request_context("/test.txt"):
        resp = serve.serve_file("test.txt")
        content = b"".join(resp.get_app_iter(flask.request.environ))
    assert resp.mimetype == "text/plain"
    assert content == b"content"


@pytest.mark.parametrize("output_path", [Path("relative")])
def test_serve_file_with_relative_output_path(output_path, app, tmp_path):
    # This excercises a bug having to do with serving files when
    # Lektor is given a relative output directory.
    #
    # E.g. via `lektor server -O outdir`
    #
    save_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        output_path.mkdir()
        test_serve_file(output_path, app)
    finally:
        os.chdir(save_cwd)


@pytest.mark.parametrize("index_html", ["index.html", "index.htm"])
def test_serve_file_dir_handling(output_path, app, index_html):
    filename = output_path / "adir" / index_html
    filename.parent.mkdir()
    filename.write_text("index")

    with app.test_request_context("/adir"):
        resp = serve.serve_file("adir")
    assert resp.status_code in (301, 308)
    assert resp.location == "adir/"

    with app.test_request_context("/adir/"):
        resp = serve.serve_file("adir/")
        content = b"".join(resp.get_app_iter(flask.request.environ))
    assert resp.status_code == 200
    assert content == b"index"


@pytest.mark.parametrize(
    "path",
    [
        "missing",
        "example/container",  # hidden page
        "adir/",  # no adir/index.{html,htm} exists
        "adir/../top.txt",  # ".." not allowed in path
        "../adir/index.txt",  # points outside of output_path
        "adir/index.txt/../index.txt",
        "adir/index.txt/../../top.txt",
        "adir/index.txt/../../adir/index.txt",
    ],
)
def test_serve_file_raises_404(output_path, app, path):
    not_an_index = output_path / "adir/index.txt"
    not_an_index.parent.mkdir()
    not_an_index.write_text("non-index")
    output_path.joinpath("top.txt").write_text("top")

    with app.test_request_context(path):
        with pytest.raises(NotFound):
            serve.serve_file(path)


################################################################


@pytest.mark.parametrize(
    "path, status, mimetype, content",
    [
        ("/hello.txt", 200, "text/plain", "Hello I am an Attachment"),
        ("/missing/", 404, "text/html", "The requested URL was not found"),
        ("/extra/container/", 404, "text/html", "Record is hidden"),
    ],
)
def test_serve(app, path, status, mimetype, content):
    with app.test_client() as c:
        resp = c.get(path)
        assert resp.status_code == status
        assert resp.mimetype == mimetype
        assert content in resp.get_data(True)


def test_serve_from_file(app, output_path):
    filename = output_path / "sub-artifact.txt"
    filename.write_text("sub-artifact")
    with app.test_client() as c:
        resp = c.get("/sub-artifact.txt")
        assert resp.status_code == 200
        assert resp.mimetype == "text/plain"


@pytest.mark.parametrize(
    "path_info, base_url, location",
    [
        ("/extra", "http://example.org/pfx/", "http://example.org/pfx/extra/"),
        (
            "/dir_with_index_html?qs",
            "http://localhost/",
            "http://localhost/dir_with_index_html/?qs",
        ),
        (
            "/projects/coffee",
            "http://localhost/pfx/",
            "http://localhost/pfx/projects/coffee/",
        ),
        ("/adir", "http://localhost/", "http://localhost/adir/"),
        ("/adir/bdir", "http://localhost/", "http://localhost/adir/bdir/"),
    ],
)
def test_serve_add_slash_redirect_integration(
    app, output_path, path_info, base_url, location
):
    output_path.joinpath("adir/bdir").mkdir(parents=True)
    with app.test_client() as c:
        resp = c.get(path_info, base_url=base_url)
        assert resp.status_code in (301, 308)
        # Be careful to accept either absolute or relative URLs in resp.location
        # See https://httpwg.org/specs/rfc7231.html#header.location
        request_url = urljoin(base_url, path_info.lstrip("/"))
        assert urljoin(request_url, resp.location) == location


@pytest.fixture
def scratch_app(scratch_env, output_path):
    lektor_info = LektorInfo(scratch_env, output_path)
    app = LektorApp(lektor_info)
    app.register_blueprint(serve.bp, url_prefix="/")
    app.add_url_rule("/ADMIN/EDIT", "url.edit", build_only=True)
    return app


def test_serve_custom_404(scratch_app, scratch_project_data):
    custom_404 = scratch_project_data / "assets/404.html"
    custom_404.parent.mkdir(exist_ok=True)
    custom_404.write_text("custom 404")

    with scratch_app.test_client() as c:
        resp = c.get("/missing.txt")
        assert resp.status_code == 404
        assert resp.mimetype == "text/html"
        assert resp.get_data(True) == "custom 404"
