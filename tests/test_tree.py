# Tests for lektor.db.Tree and related classes.
import re
import shutil
from pathlib import Path

import pytest

from lektor.constants import PRIMARY_ALT
from lektor.db import Tree
from lektor.project import Project


@pytest.fixture(scope="session")
def no_alt_pad(tmp_path_factory):
    no_alt_project = tmp_path_factory.mktemp("no-alts") / "demo-project"
    demo_project = Path(__file__).parent / "demo-project"
    shutil.copytree(demo_project, no_alt_project)

    project_file = no_alt_project / "Website.lektorproject"
    alt_section_re = r"(?ms)^\[alternatives\.\w+\].*?(?=^\[)"
    project_file.write_text(re.sub(alt_section_re, "", project_file.read_text()))

    dirs = [no_alt_project]
    while dirs:
        for child in dirs.pop().iterdir():
            if child.is_dir():
                dirs.append(child)
            elif child.match("contents+*.lr"):
                child.unlink()

    project = Project.from_path(no_alt_project)
    return project.make_env().new_pad()


@pytest.fixture(params=[False, True])
def disable_alternatives(request):
    return request.param


@pytest.fixture
def tree(pad, no_alt_pad, disable_alternatives):
    if disable_alternatives:
        pad = no_alt_pad
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
    "disable_alternatives, path, alt, expect",
    [
        (False, "/", PRIMARY_ALT, {"en": "Welcome"}),
        (False, "/test.jpg", PRIMARY_ALT, {"en": "test.jpg"}),
        (False, "/missing/gone", PRIMARY_ALT, {"en": "Gone"}),
        (False, "/projects/bagpipe", PRIMARY_ALT, {"en": "Bagpipe"}),
        (False, "/projects/bagpipe", "de", {"en": "Dudelsack"}),
        (True, "/", PRIMARY_ALT, {"en": "Welcome"}),
        (True, "/test.jpg", PRIMARY_ALT, {"en": "test.jpg"}),
        (True, "/missing/gone", PRIMARY_ALT, {"en": "Gone"}),
        (True, "/projects/bagpipe", PRIMARY_ALT, {"en": "Bagpipe"}),
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
    "disable_alternatives, path, offset, limit, order_by, expect",
    [
        (False, "/extra/container", 0, None, None, ["a", "hello.txt"]),
        (False, "/extra/container", 1, None, None, ["hello.txt"]),
        (False, "/extra/container", 0, 1, None, ["a"]),
        (False, "/projects", 0, 2, ("seq",), ["attachment.txt", "zaun"]),
        (False, "/projects", 1, 1, ("seq",), ["zaun"]),
        (False, "/projects", 0, 2, None, ["attachment.txt", "bagpipe"]),
        (False, "/projects", 8, None, None, ["slave", "wolf", "zaun"]),
        (True, "/extra/container", 0, None, None, ["a", "hello.txt"]),
        (True, "/extra/container", 1, None, None, ["hello.txt"]),
        (True, "/extra/container", 0, 1, None, ["a"]),
        (True, "/projects", 0, 2, ("seq",), ["attachment.txt", "wolf"]),
        (True, "/projects", 1, 1, ("seq",), ["wolf"]),
        (True, "/projects", 0, 2, None, ["attachment.txt", "bagpipe"]),
        (True, "/projects", 8, None, None, ["slave", "wolf"]),
    ],
)
def test_tree_item_get_children(tree, path, offset, limit, order_by, expect):
    item = tree.get(path)
    children = item.get_children(offset, limit, order_by=order_by)
    assert list(child.id for child in children) == expect


@pytest.mark.parametrize(
    "disable_alternatives, path, order_by, expect",
    [
        (False, "/", None, ["blog", "extra", "projects"]),
        (False, "/blog", ("-pub_date",), ["post2", "post1", "dummy.xml"]),
        (
            False,
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
            False,
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
        (True, "/", None, ["blog", "extra", "projects"]),
        (True, "/blog", ("-pub_date",), ["post2", "post1", "dummy.xml"]),
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


@pytest.mark.parametrize(
    "disable_alternatives, alts",
    [(False, {PRIMARY_ALT, "en", "de"}), (True, {PRIMARY_ALT})],
)
def test_tree_item_alts(tree, alts):
    item = tree.get("/")
    assert set(item.alts) == alts


@pytest.mark.parametrize(
    "disable_alternatives, path, alt, expect",
    [
        (False, "/", PRIMARY_ALT, True),
        (False, "/", "en", False),
        (False, "/", "de", False),
        (False, "/hello.txt", PRIMARY_ALT, False),
        (False, "/hello.txt", "en", False),
        (False, "/hello.txt", "de", False),
        (False, "/missing", PRIMARY_ALT, False),
        (False, "/missing", "en", False),
        (False, "/missing", "de", False),
        (False, "/projects/zaun", PRIMARY_ALT, False),
        (False, "/projects/zaun", "en", False),
        (False, "/projects/zaun", "de", True),
        (True, "/", PRIMARY_ALT, True),
        (True, "/hello.txt", PRIMARY_ALT, False),
        (True, "/missing", PRIMARY_ALT, False),
        (True, "/projects/zaun", PRIMARY_ALT, False),
    ],
)
def test_alt_exists(tree, path, alt, expect):
    item = tree.get(path)
    assert item.alts[alt].exists == expect


@pytest.mark.parametrize(
    "disable_alternatives, alt, expect",
    [
        (False, PRIMARY_ALT, False),
        (False, "en", True),
        (False, "de", False),
        (True, PRIMARY_ALT, True),
    ],
)
def test_alt_is_primary_overlay(tree, alt, expect):
    item = tree.get("/")
    assert item.alts[alt].is_primary_overlay == expect


@pytest.mark.parametrize(
    "disable_alternatives, alt, expect",
    [
        (False, PRIMARY_ALT, {"en": "English", "de": "Englisch"}),
        (False, "en", {"en": "English", "de": "Englisch"}),
        (False, "de", {"en": "German", "de": "Deutsch"}),
    ],
)
def test_alt_name_i18n(tree, alt, expect):
    item = tree.get("/")
    assert item.alts[alt].name_i18n == expect


@pytest.mark.parametrize(
    "disable_alternatives, path, alt, expect",
    [
        (False, "/", PRIMARY_ALT, "<Alt '_primary'*>"),
        (False, "/", "en", "<Alt 'en'>"),
        (False, "/", "de", "<Alt 'de'>"),
        (False, "/projects/zaun", "de", "<Alt 'de'*>"),
        (True, "/", PRIMARY_ALT, "<Alt '_primary'*>"),
        (True, "/projects/zaun", PRIMARY_ALT, "<Alt '_primary'>"),
    ],
)
def test_alt_repr(tree, path, alt, expect):
    item = tree.get(path)
    assert repr(item.alts[alt]) == expect
