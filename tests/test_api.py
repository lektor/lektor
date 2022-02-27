import os
from operator import itemgetter
from pathlib import Path
from urllib.parse import urlencode

import pytest

from lektor.admin import WebAdmin
from lektor.admin.utils import eventstream
from lektor.constants import PRIMARY_ALT


@pytest.fixture
def test_client(env, tmp_path):
    webadmin = WebAdmin(env, output_path=tmp_path / "htdocs")
    return webadmin.test_client()


@pytest.fixture
def scratch_test_client(scratch_env, tmp_path):
    webadmin = WebAdmin(scratch_env, output_path=tmp_path / "htdocs")
    return webadmin.test_client()


@pytest.fixture
def children_records_data():
    """Returns test values for children records' `id`, `title`, and `pub_date` fields."""
    return (
        {"id": "1", "title": "1 is the first number", "pub_date": "2016-07-11"},
        {
            "id": "2",
            "title": "Must be the Second item in a row",
            "pub_date": "2017-05-03",
        },
        {"id": "3", "title": "Z is the last letter", "pub_date": "2017-05-03"},
        {"id": "4", "title": "Some random string", "pub_date": "2018-05-21"},
    )


@pytest.fixture(scope="function", autouse=True)
def prepare_stub_data(scratch_project, children_records_data):
    """Creates folders, models, test object and its children records."""
    tree = scratch_project.tree
    with open(os.path.join(tree, "models", "mymodel.ini"), "w", encoding="utf-8") as f:
        f.write("[children]\n" "order_by = -pub_date, title\n")
    with open(
        os.path.join(tree, "models", "mychildmodel.ini"), "w", encoding="utf-8"
    ) as f:
        f.write(
            "[fields.title]\n" "type = string\n" "[fields.pub_date]\n" "type = date"
        )
    os.mkdir(os.path.join(tree, "content", "myobj"))
    with open(
        os.path.join(tree, "content", "myobj", "contents.lr"), "w", encoding="utf-8"
    ) as f:
        f.write("_model: mymodel\n" "---\n" "title: My Test Object\n")
    for record in children_records_data:
        os.mkdir(os.path.join(tree, "content", "myobj", record["id"]))
        with open(
            os.path.join(tree, "content", "myobj", record["id"], "contents.lr"),
            "w",
            encoding="utf-8",
        ) as f:
            f.write(
                "_model: mychildmodel\n"
                "---\n"
                "title: %s\n"
                "---\n"
                "pub_date: %s" % (record["title"], record["pub_date"])
            )


def test_children_sorting_via_api(scratch_test_client, children_records_data):
    resp = scratch_test_client.get("/admin/api/recordinfo?path=/myobj")
    assert resp.status_code == 200
    data = resp.get_json()

    children_records_ids_provided_by_api = list(map(itemgetter("id"), data["children"]))

    records_ordered_by_title = sorted(children_records_data, key=itemgetter("title"))
    ordered_records = sorted(
        records_ordered_by_title, key=itemgetter("pub_date"), reverse=True
    )

    assert (
        list(map(itemgetter("id"), ordered_records))
        == children_records_ids_provided_by_api
    )


def test_recordinfo_children_sort_limited_alts(test_client):
    # This excercises the bug described in #962, namely that
    # if a page has a child that only has content in a subset of the
    # configured alts, get_record_info throws an exception.
    resp = test_client.get("/admin/api/recordinfo?path=/projects")
    assert resp.status_code == 200
    child_data = resp.get_json()["children"]
    assert list(sorted(child_data, key=itemgetter("label"))) == child_data


def test_newrecord(scratch_test_client, scratch_project):
    params = {"path": "/", "id": "new", "data": {}}
    resp = scratch_test_client.post("/admin/api/newrecord", json=params)
    assert resp.status_code == 200
    assert resp.get_json() == {"valid_id": True, "exists": False, "path": "/new"}
    assert Path(scratch_project.tree, "content", "new", "contents.lr").exists()


def test_newrecord_bad_path(scratch_test_client, scratch_project):
    params = {"path": "/../../templates", "id": "", "data": {}}
    resp = scratch_test_client.post("/admin/api/newrecord", json=params)
    assert resp.status_code == 400
    assert resp.get_data(as_text=True) == "Invalid path"


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
