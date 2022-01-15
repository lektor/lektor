# Tests for lektor.db.Tree and related classes.
import pytest

from lektor.constants import PRIMARY_ALT
from lektor.db import Tree


@pytest.fixture
def tree(pad):
    return Tree(pad)


@pytest.mark.parametrize(
    "path, expect",
    [
        ("/", ""),
        ("/blog", "blog"),
        ("/this/is/missing", "missing"),
    ],
)
def test_tree_item_id(tree, path, expect):
    item = tree.get(path)
    assert item.path == path
    assert item.id == expect


@pytest.mark.parametrize(
    "path, expect",
    [
        ("/", True),
        ("/test.jpg", True),
        ("/missing", False),
    ],
)
def test_tree_item_exists(tree, path, expect):
    item = tree.get(path)
    assert item.exists is expect
    if not item.exists:
        assert item._datamodel is None


@pytest.mark.parametrize(
    "path, expect",
    [
        ("/", False),
        ("/test.jpg", True),
        ("/missing", False),
    ],
)
def test_tree_item_can_be_deleted(tree, path, expect):
    item = tree.get(path)
    assert item.can_be_deleted == expect


@pytest.mark.parametrize(
    "path, expect",
    [
        ("/", True),
        ("/test.jpg", True),
        ("/missing", True),
        ("/extra/container", False),
    ],
)
def test_tree_item_is_visible(tree, path, expect):
    item = tree.get(path)
    assert item.is_visible == expect


@pytest.mark.parametrize(
    "path, is_attachment, attachment_type",
    [
        ("/", False, None),
        ("/test.jpg", True, "image"),
        ("/missing", False, None),
    ],
)
def test_tree_item_is_attachment(tree, path, is_attachment, attachment_type):
    item = tree.get(path)
    assert item.is_attachment is is_attachment
    assert item.attachment_type == attachment_type


@pytest.mark.parametrize(
    "path, expect",
    [
        ("/", True),
        ("/test.jpg", False),
        ("/missing", False),
    ],
)
def test_tree_item_can_have_children(tree, path, expect):
    item = tree.get(path)
    assert item.can_have_children == expect
    # NB: currently in the demo-project, can_have_children ==
    # can_have_attachments
    assert item.can_have_attachments == expect


@pytest.mark.parametrize(
    "path, alt, expect",
    [
        ("/", PRIMARY_ALT, {"en": "Welcome"}),
        ("/test.jpg", PRIMARY_ALT, {"en": "test.jpg"}),
        ("/missing/gone", PRIMARY_ALT, {"en": "Gone"}),
        ("/projects/bagpipe", PRIMARY_ALT, {"en": "Bagpipe"}),
        ("/projects/bagpipe", "de", {"en": "Dudelsack"}),
    ],
)
def test_tree_item_get_record_label_i18n(tree, path, alt, expect):
    item = tree.get(path)
    assert item.get_record_label_i18n(alt) == expect


@pytest.mark.parametrize(
    "path, expect",
    [
        ("/", None),
        ("/blog", "blog-post"),
    ],
)
def test_tree_implied_child_datamodel(tree, path, expect):
    item = tree.get(path)
    assert item.implied_child_datamodel == expect


@pytest.mark.parametrize(
    "path, parent_path",
    [
        ("/", None),
        ("/test.jpg", "/"),
        ("/missing/gone", "/missing"),
        ("/projects/bagpipe", "/projects"),
    ],
)
def test_get_parent(tree, path, parent_path):
    item = tree.get(path)
    parent = item.get_parent()
    assert (parent and parent.path) == parent_path


@pytest.mark.parametrize(
    "path, name",
    [
        ("/", "a"),
        ("/missing/gone", "foo"),
    ],
)
def test_get(tree, path, name):
    item = tree.get(path)
    assert item.get(name).id == name


@pytest.mark.parametrize(
    "path, offset, limit, order_by, expect",
    [
        ("/extra/container", 0, None, None, ["a", "hello.txt"]),
        ("/extra/container", 1, None, None, ["hello.txt"]),
        ("/extra/container", 0, 1, None, ["a"]),
        ("/projects", 0, 2, ("seq",), ["attachment.txt", "zaun"]),
        ("/projects", 1, 1, ("seq",), ["zaun"]),
        ("/projects", 0, 2, None, ["attachment.txt", "bagpipe"]),
        ("/projects", 9, None, None, ["wolf", "zaun"]),
    ],
)
def test_tree_item_get_children(tree, path, offset, limit, order_by, expect):
    item = tree.get(path)
    children = item.get_children(offset, limit, order_by=order_by)
    assert list(child.id for child in children) == expect


@pytest.mark.parametrize(
    "path, order_by, expect",
    [
        ("/", None, ["blog", "extra", "projects"]),
        ("/blog", ("-pub_date",), ["post2", "post1", "dummy.xml"]),
        (
            "/projects",
            ("seq",),
            [
                "zaun",
                "wolf",
                "slave",
                "secret",
                "postage",
                "oven",
                "master",
                "filtered",
                "bagpipe",
                "coffee",
            ],
        ),
        (
            "/projects",
            None,
            [
                "bagpipe",
                "coffee",
                "filtered",
                "master",
                "oven",
                "postage",
                "secret",
                "slave",
                "wolf",
                "zaun",
            ],
        ),
    ],
)
def test_tree_item_iter_subpages(tree, path, order_by, expect):
    item = tree.get(path)
    assert list(child.id for child in item.iter_subpages(order_by)) == expect


@pytest.mark.parametrize(
    "path, expect",
    [
        (
            "/",
            [
                "hello.txt",
                "test-progressive.jpg",
                "test-sof-last.jpg",
                "test.jpg",
                "test.mp4",
            ],
        ),
    ],
)
def test_tree_item_iter_attachments(tree, path, expect):
    item = tree.get(path)
    assert list(child.id for child in item.iter_attachments()) == expect


@pytest.mark.parametrize(
    "path, order_by, expect",
    [
        ("/", ("title",), [("Welcome", False)]),
        ("/extra", ("title", "+_id"), [("Hello", False), ("extra", False)]),
        ("/missing", ("title", "-_id"), [(None, False), ("missing", True)]),
    ],
)
def test_tree_item_get_order_by(tree, path, order_by, expect):
    item = tree.get(path)
    sort_key = item.get_sort_key(order_by)
    assert [(_.value, _.reverse) for _ in sort_key] == expect


@pytest.mark.parametrize(
    "path, expect",
    [
        ("/", "<TreeItem '/'>"),
        ("/hello.txt", "<TreeItem '/hello.txt' attachment>"),
    ],
)
def test_tree_item_repr(tree, path, expect):
    item = tree.get(path)
    assert repr(item) == expect


def test_tree_item_alts(tree):
    item = tree.get("/")
    assert set(item.alts) == {PRIMARY_ALT, "en", "de"}


@pytest.mark.parametrize(
    "path, alt, expect",
    [
        ("/", PRIMARY_ALT, True),
        ("/", "en", False),
        ("/", "de", False),
        ("/hello.txt", PRIMARY_ALT, False),
        ("/hello.txt", "en", False),
        ("/hello.txt", "de", False),
        ("/missing", PRIMARY_ALT, False),
        ("/missing", "en", False),
        ("/missing", "de", False),
        ("/projects/zaun", PRIMARY_ALT, False),
        ("/projects/zaun", "en", False),
        ("/projects/zaun", "de", True),
    ],
)
def test_alt_exists(tree, path, alt, expect):
    item = tree.get(path)
    assert item.alts[alt].exists == expect


@pytest.mark.parametrize(
    "alt, expect",
    [
        (PRIMARY_ALT, False),
        ("en", True),
        ("de", False),
    ],
)
def test_alt_is_primary_overlay(tree, alt, expect):
    item = tree.get("/")
    assert item.alts[alt].is_primary_overlay == expect


@pytest.mark.parametrize(
    "alt, expect",
    [
        (PRIMARY_ALT, {"en": "English", "de": "Englisch"}),
        ("en", {"en": "English", "de": "Englisch"}),
        ("de", {"en": "German", "de": "Deutsch"}),
    ],
)
def test_alt_name_i18n(tree, alt, expect):
    item = tree.get("/")
    assert item.alts[alt].name_i18n == expect


@pytest.mark.parametrize(
    "path, alt, expect",
    [
        ("/", PRIMARY_ALT, "<Alt '_primary'*>"),
        ("/", "en", "<Alt 'en'>"),
        ("/", "de", "<Alt 'de'>"),
        ("/projects/zaun", "de", "<Alt 'de'*>"),
    ],
)
def test_alt_repr(tree, path, alt, expect):
    item = tree.get(path)
    assert repr(item.alts[alt]) == expect
