import pytest

from lektor.editor import EditorSession


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


@pytest.fixture
def original_data():
    return {"_id": "test", "item1": "value1"}


@pytest.fixture
def fallback_data():
    return {"_id": "test", "item1": "fallback1", "item2": "fallback2"}


@pytest.fixture
def editor_data(pad, original_data, fallback_data):
    return EditorSession(
        pad,
        "id",
        "path",
        original_data,
        fallback_data,
        "datamodel",
        "record",
    )


def ischanged(editor_data):
    return len(editor_data._changed) > 0


def test_editor_data_getitem(editor_data):
    assert editor_data["_id"] == "test"
    assert editor_data["item1"] == "value1"
    assert editor_data["item2"] == "fallback2"
    with pytest.raises(KeyError):
        editor_data["item3"]  # pylint: disable=pointless-statement


def test_editor_data_setitem(editor_data):
    with pytest.raises(KeyError):
        editor_data["_path"] = "newpath"
    assert not ischanged(editor_data)

    editor_data["item1"] = "newval"
    assert editor_data["item1"] == "newval"
    assert ischanged(editor_data)

    editor_data["item1"] = "value1"
    assert editor_data["item1"] == "value1"
    assert not ischanged(editor_data)


def test_editor_data_setitem_possibly_implied_key(editor_data, original_data):
    original_data["_model"] = "mymodel"
    assert not ischanged(editor_data)
    editor_data["_model"] = "mymodel"
    assert ischanged(editor_data)


def test_editor_data_delitem(editor_data):
    del editor_data["item1"]
    assert ischanged(editor_data)
    assert "item1" not in editor_data

    editor_data["item1"] = "newval"
    assert ischanged(editor_data)
    assert "item1" in editor_data

    editor_data["item1"] = "value1"
    assert not ischanged(editor_data)
    assert "item1" in editor_data


def test_editor_data_delitem_raises_keyerror(editor_data):
    with pytest.raises(KeyError):
        del editor_data["missing"]
    with pytest.raises(KeyError):
        del editor_data["_id"]


def test_revert_key(editor_data):
    editor_data["item2"] = "xx"
    assert ischanged(editor_data)
    editor_data.revert_key("item2")
    assert not ischanged(editor_data)
    assert editor_data["item2"] == "fallback2"


def test_editor_data_iter(editor_data):
    assert list(editor_data) == ["item1", "item2"]
    editor_data["item3"] = "new3"
    assert list(editor_data) == ["item1", "item2", "item3"]
    del editor_data["item1"]
    assert list(editor_data) == ["item2", "item3"]


def test_editor_data_len(editor_data):
    assert len(editor_data) == 2
    del editor_data["item1"]
    assert len(editor_data) == 1
    editor_data["item3"] = "new3"
    assert len(editor_data) == 2


def test_editor_data_keys(editor_data):
    assert list(editor_data.keys()) == ["item1", "item2"]
    assert "item1" in editor_data.keys()
    assert len(editor_data.keys()) == 2

    assert list(editor_data.keys(fallback=False)) == ["item1"]
    assert "item2" not in editor_data.keys(fallback=False)
    assert len(editor_data.keys(fallback=False)) == 1


def test_editor_data_items(editor_data):
    assert list(editor_data.items(fallback=False)) == [
        ("item1", "value1"),
    ]
    assert ("item2", "fallback2") not in editor_data.items(fallback=False)
    assert len(editor_data.items(fallback=False)) == 1

    editor_data["item3"] = "x3"
    assert list(editor_data.items()) == [
        ("item1", "value1"),
        ("item2", "fallback2"),
        ("item3", "x3"),
    ]
    assert ("item2", "fallback2") in editor_data.items()
    assert ("item3", "x3") in editor_data.items()
    assert len(editor_data.items()) == 3


def test_editor_data_values(editor_data):
    del editor_data["item1"]
    assert list(editor_data.values()) == ["fallback2"]
    assert "fallback2" in editor_data.values()
    assert len(editor_data.values()) == 1

    assert list(editor_data.values(fallback=False)) == []
    assert "fallback2" not in editor_data.values(fallback=False)
    assert len(editor_data.values(fallback=False)) == 0
