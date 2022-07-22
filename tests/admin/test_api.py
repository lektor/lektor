from inspect import cleandoc
from io import BytesIO
from operator import itemgetter
from pathlib import Path
from urllib.parse import urlencode

import pytest

from lektor.admin import WebAdmin
from lektor.admin.context import LektorContext
from lektor.admin.utils import eventstream
from lektor.builder import Builder
from lektor.constants import PRIMARY_ALT
from lektor.db import Database
from lektor.editor import EditorSession
from lektor.environment import Environment
from lektor.project import Project
from lektor.publisher import PublishError


def write_text(path, text):
    path.parent.mkdir(exist_ok=True)
    path.write_text(cleandoc(text))


@pytest.fixture
def scratch_project_data(scratch_project_data):
    write_text(
        scratch_project_data / "content/page/contents.lr",
        """
        _model: page
        ---
        title: A Page
        """,
    )
    return scratch_project_data


@pytest.fixture
def scratch_client(scratch_env, scratch_project):
    webadmin = WebAdmin(scratch_env, output_path=scratch_project.tree)
    with webadmin.test_client() as client:
        yield client


@pytest.fixture
def scratch_content_path(scratch_project):
    return Path(scratch_project.tree) / "content"


@pytest.fixture(scope="session")
def project_path(data_path):
    return data_path / "demo-project"


@pytest.fixture(scope="session")
def webadmin(tmp_path_factory, project_path):
    project = Project.from_path(project_path)
    env = Environment(project, load_plugins=False)
    output_path = tmp_path_factory.mktemp("webadmin-output")

    pad = Database(env).new_pad()
    builder = Builder(pad, output_path)
    builder.update_all_source_infos()

    app = WebAdmin(env, output_path=output_path)
    return app


@pytest.fixture
def test_client(webadmin):
    with webadmin.test_client() as client:
        yield client


def test_recordinfo_children_sort_limited_alts(test_client):
    # This exercises the bug described in #962, namely that
    # if a page has a child that only has content in a subset of the
    # configured alts, get_record_info throws an exception.
    data = test_client.get("/admin/api/recordinfo?path=/projects").get_json()
    child_data = data["children"]
    assert list(sorted(child_data, key=itemgetter("label"))) == child_data


def test_eventstream_yield_bytes():
    count = 0

    @eventstream
    def testfunc():
        yield "string"
        yield 5

    for data in testfunc().response:  # pylint: disable=no-member
        count += 1
        assert isinstance(data, bytes)
    assert count >= 2


@pytest.mark.parametrize(
    "endpoint, params, invalid",
    [
        ("recordinfo", {}, {"path"}),
        ("previewinfo", {"path": "/", "alt": "BAD"}, {"alt"}),
    ],
)
def test_invalid_params(test_client, endpoint, params, invalid):
    resp = test_client.get(f"/admin/api/{endpoint}?{urlencode(params)}")
    assert resp.status_code == 400
    error = resp.get_json()["error"]
    assert error["title"] == "Invalid parameters"
    assert set(error["messages"].keys()) == invalid


def test_recordinfo(test_client):
    resp = test_client.get("/admin/api/recordinfo?path=%2F")
    assert resp.status_code == 200
    data = resp.get_json()
    assert any(att["id"] == "hello.txt" for att in data["attachments"])
    assert any(page["id"] == "blog" for page in data["children"])
    assert any(alt["alt"] == "de" for alt in data["alts"])


def test_delete_field(scratch_client, scratch_content_path):
    # None in page data means to delete the field
    # Test that that works
    contents_lr = scratch_content_path / "contents.lr"

    assert "\nbody:" in contents_lr.read_text()
    resp = scratch_client.put(
        "/admin/api/rawrecord?path=%2F", json={"path": "/", "data": {"body": None}}
    )
    assert resp.status_code == 200
    assert "\nbody:" not in contents_lr.read_text()


def test_get_path_info(test_client):
    resp = test_client.get("/admin/api/pathinfo?path=%2Fblog%2Fpost2")
    assert resp.get_json() == {
        "segments": [
            {
                "can_have_children": True,
                "exists": True,
                "id": "",
                "label_i18n": {"en": "Welcome"},
                "path": "/",
            },
            {
                "can_have_children": True,
                "exists": True,
                "id": "blog",
                "label_i18n": {"en": "Blog"},
                "path": "/blog",
            },
            {
                "can_have_children": True,
                "exists": True,
                "id": "post2",
                "label_i18n": {"en": "Post 2"},
                "path": "/blog/post2",
            },
        ],
    }


@pytest.mark.parametrize(
    "path, expect",
    [
        (
            "/blog/post1/hello.txt",
            {
                "exists": True,
                "url": "/blog/2015/12/post1/hello.txt",
                "is_hidden": False,
            },
        ),
        (
            "/extra/container",
            {
                "exists": True,
                "url": "/extra/container/",
                "is_hidden": True,
            },
        ),
        (
            "/missing",
            {
                "exists": False,
                "url": None,
                "is_hidden": True,
            },
        ),
    ],
)
def test_previewinfo(test_client, path, expect):
    resp = test_client.get(f"/admin/api/previewinfo?{urlencode({'path': path})}")
    assert resp.status_code == 200
    assert resp.get_json() == expect


@pytest.mark.parametrize("use_json", [True, False])
@pytest.mark.parametrize("lang", ["en", None])
def test_find(test_client, use_json, lang):
    # Test that we can pass params in JSON body, rather than in the query
    params = {"q": "hello", "alt": "_primary", "lang": lang}
    if use_json:
        resp = test_client.post("/admin/api/find", json=params)
    else:
        resp = test_client.post(f"/admin/api/find?{urlencode(params)}")
    assert resp.status_code == 200
    results = resp.get_json()["results"]
    assert any(result["title"] == "Hello" for result in results)
    assert len(results) == 1


@pytest.mark.parametrize(
    "path, alt, srcfile",
    [
        ("/projects/bagpipe", "de", "projects/bagpipe/contents+de.lr"),
        ("/hello.txt", "de", "hello.txt"),
    ],
)
def test_browsefs(test_client, mocker, project_path, path, alt, srcfile):
    launch = mocker.patch("click.launch")
    params = {"path": path, "alt": alt}
    resp = test_client.post("/admin/api/browsefs", json=params)
    assert resp.status_code == 200
    assert resp.get_json()["okay"]
    assert launch.mock_calls == [
        mocker.call(str(project_path / "content" / srcfile), locate=True),
    ]


@pytest.mark.parametrize(
    "path, alt, can_have_children",
    [
        ("/test.jpg", "de", False),
        ("/projects", "de", True),
    ],
)
def test_get_new_record_info(test_client, path, alt, can_have_children):
    params = {"path": path, "alt": alt}
    resp = test_client.get(f"/admin/api/newrecord?{urlencode(params)}")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["can_have_children"] is bool(can_have_children)


@pytest.mark.parametrize(
    "path, alt, can_upload",
    [
        ("/test.jpg", "de", False),
        ("/projects", "de", True),
    ],
)
def test_get_new_attachment_info(test_client, path, alt, can_upload):
    params = {"path": path}
    resp = test_client.get(f"/admin/api/newattachment?{urlencode(params)}")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["can_upload"] is bool(can_upload)


def test_upload_new_attachment(scratch_client, scratch_content_path):
    params = {
        "path": "/page",
        "file": (BytesIO(b"foo data"), "foo.txt"),
    }
    resp = scratch_client.post("/admin/api/newattachment", data=params)
    assert resp.status_code == 200
    assert not resp.get_json()["bad_upload"]
    dstpath = scratch_content_path / "page/foo.txt"
    assert dstpath.read_bytes() == b"foo data"


@pytest.mark.parametrize(
    "path, alt",
    [
        ("/test.txt", PRIMARY_ALT),
        ("/missing", PRIMARY_ALT),
        ("/missing", "de"),
    ],
)
def test_upload_new_attachment_failure(scratch_client, scratch_content_path, path, alt):
    scratch_content_path.joinpath("test.txt").write_bytes(b"test")
    params = {
        "path": path,
        "alt": alt,
        "file": (BytesIO(b"foo data"), "foo.txt"),
    }
    resp = scratch_client.post("/admin/api/newattachment", data=params)
    assert resp.status_code == 200
    assert resp.get_json()["bad_upload"]
    dstpath = scratch_content_path / "test.txt/foo.txt"
    assert not dstpath.exists()


@pytest.mark.parametrize(
    "path, id, expect, creates",
    [
        (
            "/page",
            "new",
            {"valid_id": True, "exists": False, "path": "/page/new"},
            "page/new/contents.lr",
        ),
        ("/page", ".new", {"valid_id": False, "exists": False, "path": None}, None),
        ("/", "page", {"valid_id": True, "exists": True, "path": "/page"}, None),
    ],
)
def test_add_new_record(
    scratch_client, scratch_content_path, path, id, expect, creates
):
    params = {"path": path, "id": id, "data": {}}
    resp = scratch_client.post("/admin/api/newrecord", json=params)
    assert resp.status_code == 200
    assert resp.get_json() == expect
    if creates is not None:
        dstpath = scratch_content_path / creates
        assert dstpath.exists()


@pytest.mark.parametrize(
    "delete_master, expect", [("1", True), (True, True), ("0", False), (False, False)]
)
def test_delete_record(scratch_client, mocker, delete_master, expect):
    delete = mocker.patch.object(EditorSession, "delete")
    params = {"path": "/myobj", "delete_master": delete_master}
    resp = scratch_client.post("/admin/api/deleterecord", json=params)
    assert resp.status_code == 200
    assert delete.mock_calls == [
        mocker.call(delete_master=expect),
    ]


@pytest.mark.parametrize(
    "url_path, expect",
    [
        (
            "/blog/2015/12/post1/hello.txt",
            {
                "exists": True,
                "path": "/blog/post1/hello.txt",
                "alt": PRIMARY_ALT,
            },
        ),
        (
            "/missing",
            {
                "exists": False,
                "path": None,
                "alt": None,
            },
        ),
        (
            "/static/demo.css",  # non-Records do not exist
            {
                "exists": False,
                "path": None,
                "alt": None,
            },
        ),
    ],
)
def test_match_url(test_client, url_path, expect):
    params = {"url_path": url_path}
    resp = test_client.get(f"/admin/api/matchurl?{urlencode(params)}")
    assert resp.status_code == 200
    assert resp.get_json() == expect


def test_get_raw_records(test_client):
    resp = test_client.get("/admin/api/rawrecord?path=%2F")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["data"]["title"] == "Welcome"
    assert "datamodel" in data


def test_servers(test_client):
    resp = test_client.get("/admin/api/servers")
    assert resp.status_code == 200
    assert any(server["id"] == "production" for server in resp.get_json()["servers"])


def test_build(test_client, webadmin, mocker):
    builder = mocker.patch.object(LektorContext, "builder")
    resp = test_client.post("/admin/api/build")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["okay"]
    assert builder.mock_calls == [
        mocker.call.build_all(),
        mocker.call.prune(),
    ]


def test_clean(test_client, webadmin, mocker):
    builder = mocker.patch.object(LektorContext, "builder")
    resp = test_client.post("/admin/api/clean")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["okay"]
    assert mocker.call.prune(all=True) in builder.mock_calls


@pytest.mark.xfail(reason="FIXME")
def test_publish_requires_post(test_client, mocker):
    # See https://github.com/lektor/lektor/issues/1006
    resp = test_client.get("/admin/api/publish?server=unknown")
    assert resp.status_code == 405


def test_publish(test_client, mocker):
    def dummy_publish(env, target, output_path, credentials=None, **extra):
        yield "line1"
        raise PublishError("wups")

    mocker.patch("lektor.admin.modules.api.publish", side_effect=dummy_publish)

    resp = test_client.get("/admin/api/publish?server=production")
    assert resp.status_code == 200
    assert list(resp.response) == [
        b'data: {"msg": "line1"}\n\n',
        b'data: {"msg": "Error: wups"}\n\n',
        b"data: null\n\n",
    ]


@pytest.mark.parametrize(
    "params",
    [
        {"server": "bogus"},
        {},
    ],
)
def test_publish_bad_params(test_client, params):
    resp = test_client.get(f"/admin/api/publish?{urlencode(params)}")
    assert resp.status_code == 400
    assert "server" in resp.get_json()["error"]["messages"]


def test_ping(test_client):
    resp = test_client.get("/admin/api/ping")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["okay"]


@pytest.mark.parametrize(
    "url",
    [
        "/missing.txt",
        "/admin/missing.txt",
        "/admin/api/missing.txt",
        "/admin/api/edit/missing.txt",
    ],
)
def test_missing_files(test_client, url):
    resp = test_client.get(url)
    assert resp.status_code == 404


@pytest.mark.parametrize(
    "url, allowed",
    [
        ("/", {"GET"}),
        ("/admin/api/recordinfo?path=%2F", {"GET"}),
        ("/admin/api/clean", {"POST"}),
        ("/admin/api/rawrecord", {"GET", "PUT"}),
    ],
)
@pytest.mark.parametrize("method", {"GET", "POST", "PUT"})
def test_allowed_methods(test_client, method, url, allowed):
    if method not in allowed:
        extra_allowed = {"OPTIONS", "HEAD"} if "GET" in allowed else {"OPTIONS"}
        resp = test_client.open(url, method=method)
        assert resp.status_code == 405
        assert set(resp.allow) == allowed | extra_allowed
