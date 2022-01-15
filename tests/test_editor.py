import pytest

from lektor.editor import BadEdit
from lektor.editor import make_editor_session
from lektor.editor import MutableEditorData


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
    "path, kwargs, expect",
    [
        ("projects/zaun", {"alt": "xx"}, "invalid alternative"),
        ("projects/.zaun", {}, "Invalid ID"),
        ("projects", {"is_attachment": True}, "attachment flag"),
        ("projects", {"datamodel": "page"}, "datamodel"),
        pytest.param(
            # model conflict with that of existing alt
            #
            # Different alts of the same page should not be able to have different
            # models, right?
            "projects/zaun",
            {"alt": "en", "datamodel": "page"},
            "conflicting",
            marks=pytest.mark.xfail(reason="buglet that should be fixed"),
        ),
    ],
)
def test_make_editor_session_raises_bad_edit(pad, path, kwargs, expect):
    with pytest.raises(BadEdit) as excinfo:
        make_editor_session(pad, path, **kwargs)
    assert expect in str(excinfo.value)


def test_basic_editor(scratch_tree):
    sess = scratch_tree.edit("/")

    assert sess.id == ""
    assert sess.path == "/"
    assert sess.record is not None

    assert sess.data["_model"] == "page"
    assert sess.data["title"] == "Index"
    assert sess.data["body"] == "*Hello World!*"

    sess.data["body"] = "A new body"
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

    assert sess.data["_model"] == "page"
    assert sess.data["title"] == "Index"
    assert sess.data["body"] == "*Hello World!*"

    sess.data["body"] = "Hallo Welt!"
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
def editor_data(original_data, fallback_data):
    return MutableEditorData(original_data, fallback_data)


def test_editor_data_ischanged(editor_data):
    assert not editor_data.ischanged()
    editor_data["item2"] = "fallback2"
    assert not editor_data.ischanged()
    editor_data["item2"] = "new2"
    assert editor_data.ischanged()
    editor_data["item2"] = "fallback2"
    assert not editor_data.ischanged()


def test_editor_data_getitem(editor_data):
    assert editor_data["_id"] == "test"
    assert editor_data["item1"] == "value1"
    assert editor_data["item2"] == "fallback2"
    with pytest.raises(KeyError):
        editor_data["item3"]  # pylint: disable=pointless-statement


def test_editor_data_setitem(editor_data):
    with pytest.raises(KeyError):
        editor_data["_path"] = "newpath"
    assert not editor_data.ischanged()

    editor_data["item1"] = "newval"
    assert editor_data["item1"] == "newval"
    assert editor_data.ischanged()

    editor_data["item1"] = "value1"
    assert editor_data["item1"] == "value1"
    assert not editor_data.ischanged()


def test_editor_data_setitem_possibly_implied_key(editor_data, original_data):
    original_data["_model"] = "mymodel"
    assert not editor_data.ischanged()
    editor_data["_model"] = "mymodel"
    assert editor_data.ischanged()


def test_editor_data_delitem(editor_data):
    del editor_data["item1"]
    assert editor_data.ischanged()
    assert "item1" not in editor_data

    editor_data["item1"] = "newval"
    assert editor_data.ischanged()
    assert "item1" in editor_data

    editor_data["item1"] = "value1"
    assert not editor_data.ischanged()
    assert "item1" in editor_data


def test_editor_data_delitem_raises_keyerror(editor_data):
    with pytest.raises(KeyError):
        del editor_data["missing"]
    with pytest.raises(KeyError):
        del editor_data["_id"]


def test_revert_key(editor_data):
    editor_data["item2"] = "xx"
    assert editor_data.ischanged()
    editor_data.revert_key("item2")
    assert not editor_data.ischanged()
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


def test_deprecated_data_proxy_methods(pad):
    editor = make_editor_session(pad, "/")

    with pytest.deprecated_call(match=r"EditorSession\.__contains__ .* deprecated"):
        assert "arbitrary" not in editor

    with pytest.deprecated_call(match=r"EditorSession\.__setitem__ .* deprecated"):
        editor["test"] = "value"
    assert editor.data["test"] == "value"
    with pytest.deprecated_call(match=r"EditorSession\.__getitem__ .* deprecated"):
        assert editor["test"] == "value"

    with pytest.deprecated_call(match=r"EditorSession\.update .* deprecated"):
        editor.update({"test": "another"})
    assert editor.data["test"] == "another"

    items = set(editor.data.items())
    with pytest.deprecated_call(match=r"EditorSession\.__len__ .* deprecated"):
        assert len(editor) == len(items)
    with pytest.deprecated_call(match=r"EditorSession\.items .* deprecated"):
        assert set(editor.items()) == items
    with pytest.deprecated_call(match=r"EditorSession\.__iter__ .* deprecated"):
        assert set(editor) == set(key for key, val in items)
    with pytest.deprecated_call(match=r"EditorSession\.keys .* deprecated"):
        assert set(editor.keys()) == set(key for key, val in items)
    with pytest.deprecated_call(match=r"EditorSession\.values .* deprecated"):
        assert set(editor.values()) == set(val for key, val in items)

    with pytest.deprecated_call(match=r"EditorSession\.iteritems .*\.data\.items "):
        assert set(editor.iteritems()) == items
    with pytest.deprecated_call(match=r"EditorSession\.iterkeys .*\.data\.keys "):
        assert set(editor.iterkeys()) == set(key for key, val in items)
    with pytest.deprecated_call(match=r"EditorSession\.itervalues .*\.data\.values "):
        assert set(editor.itervalues()) == set(val for key, val in items)

    with pytest.deprecated_call(match=r"EditorSession\.revert_key .* deprecated"):
        editor.revert_key("test")
    assert "test" not in editor.data
