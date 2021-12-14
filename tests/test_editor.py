import pytest

from lektor.editor import BadEdit
from lektor.editor import make_editor_session


@pytest.mark.parametrize(
    "path, kwargs, expect",
    [
        ("new", {}, {"exists": False, "datamodel": "page"}),
        ("new", {"alt": "en"}, {"exists": False, "datamodel": "page"}),
        ("projects/new", {}, {"exists": False, "datamodel": "project"}),
        ("projects/new", {"datamodel": "page"}, {"exists": False, "datamodel": "page"}),
        ("projects/zaun", {"alt": "de"}, {"exists": True, "datamodel": "project"}),
        ("projects/zaun", {"alt": "en"}, {"exists": False}),
        ("projects/zaun", {}, {"exists": False}),
        ("projects/zaun", {"alt": "_primary"}, {"exists": False}),
    ],
)
def test_make_editor_session(pad, path, kwargs, expect):
    sess = make_editor_session(pad, path, **kwargs)
    if "exists" in expect:
        assert sess.exists == expect["exists"]
    if "datamodel" in expect:
        assert sess.datamodel.id == expect["datamodel"]


@pytest.mark.parametrize(
    "path, kwargs",
    [
        ("projects/zaun", {"alt": "xx"}),  # invalid alt
        ("projects/.zaun", {}),  # invalid id
        ("projects", {"is_attachment": True}),  # not an attachment
        ("projects", {"datamodel": "page"}),  # attempt to change model
    ],
)
def test_make_editor_session_raises_bad_edit(pad, path, kwargs):
    with pytest.raises(BadEdit):
        make_editor_session(pad, path, **kwargs)


def test_basic_editor(scratch_tree):
    sess = scratch_tree.edit("/")

    assert sess.id == ""
    assert sess.path == "/"
    assert sess.record is not None

    assert sess["_model"] == "page"
    assert sess["title"] == "Index"
    assert sess["body"] == "*Hello World!*"

    sess["body"] = "A new body"
    sess.commit()

    assert sess.closed

    with open(sess.get_fs_path(), encoding="utf-8") as f:
        assert f.read().splitlines() == [
            "_model: page",
            "---",
            "title: Index",
            "---",
            "body: A new body",
        ]


def test_create_alt(scratch_tree, scratch_pad):
    sess = scratch_tree.edit("/", alt="de")

    assert sess.id == ""
    assert sess.path == "/"
    assert sess.record is not None

    assert sess["_model"] == "page"
    assert sess["title"] == "Index"
    assert sess["body"] == "*Hello World!*"

    sess["body"] = "Hallo Welt!"
    sess.commit()

    assert sess.closed

    # When we use the editor to change this, we only want the fields that
    # changed compared to the base to be included.
    with open(sess.get_fs_path(alt="de"), encoding="utf-8") as f:
        assert f.read().splitlines() == ["body: Hallo Welt!"]

    scratch_pad.cache.flush()
    item = scratch_pad.get("/", alt="de")
    assert item["_slug"] == ""
    assert item["title"] == "Index"
    assert item["body"].source == "Hallo Welt!"
    assert item["_model"] == "page"
