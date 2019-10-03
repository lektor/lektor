import os
from operator import itemgetter

import pytest
from flask import json

from lektor.admin import WebAdmin


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
    with open(os.path.join(tree, "models", "mymodel.ini"), "w") as f:
        f.write("[children]\n" "order_by = -pub_date, title\n")
    with open(os.path.join(tree, "models", "mychildmodel.ini"), "w") as f:
        f.write(
            "[fields.title]\n" "type = string\n" "[fields.pub_date]\n" "type = date"
        )
    os.mkdir(os.path.join(tree, "content", "myobj"))
    with open(os.path.join(tree, "content", "myobj", "contents.lr"), "w") as f:
        f.write("_model: mymodel\n" "---\n" "title: My Test Object\n")
    for record in children_records_data:
        os.mkdir(os.path.join(tree, "content", "myobj", record["id"]))
        with open(
            os.path.join(tree, "content", "myobj", record["id"], "contents.lr"), "w"
        ) as f:
            f.write(
                "_model: mychildmodel\n"
                "---\n"
                "title: %s\n"
                "---\n"
                "pub_date: %s" % (record["title"], record["pub_date"])
            )


def test_children_sorting_via_api(scratch_project, scratch_env, children_records_data):
    webadmin = WebAdmin(scratch_env, output_path=scratch_project.tree)
    data = json.loads(
        webadmin.test_client().get("/admin/api/recordinfo?path=/myobj").data
    )
    children_records_ids_provided_by_api = list(map(itemgetter("id"), data["children"]))

    records_ordered_by_title = sorted(children_records_data, key=itemgetter("title"))
    ordered_records = sorted(
        records_ordered_by_title, key=itemgetter("pub_date"), reverse=True
    )

    assert (
        list(map(itemgetter("id"), ordered_records))
        == children_records_ids_provided_by_api
    )


def test_eventstream_yield_bytes():
    count = 0
    from lektor.admin.utils import eventstream

    @eventstream
    def testfunc():
        yield "string"
        yield 5

    for data in testfunc().response:  # pylint: disable=no-member
        count += 1
        assert isinstance(data, bytes)
    assert count >= 2
