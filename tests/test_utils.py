# coding: utf-8
import pytest

from lektor.utils import build_url
from lektor.utils import is_path_child_of
from lektor.utils import join_path
from lektor.utils import magic_split_ext
from lektor.utils import make_relative_url
from lektor.utils import parse_path
from lektor.utils import slugify


def test_join_path():

    assert join_path("a", "b") == "a/b"
    assert join_path("/a", "b") == "/a/b"
    assert join_path("a@b", "c") == "a@b/c"
    assert join_path("a@b", "") == "a@b"
    assert join_path("a@b", "@c") == "a@c"
    assert join_path("a@b/c", "a@b") == "a/a@b"

    assert join_path("blog@archive", "2015") == "blog@archive/2015"
    assert join_path("blog@archive/2015", "..") == "blog@archive"
    assert join_path("blog@archive/2015", "@archive") == "blog@archive"
    assert join_path("blog@archive", "..") == "blog"
    assert join_path("blog@archive", ".") == "blog@archive"
    assert join_path("blog@archive", "") == "blog@archive"

    # special behavior: parent of pagination paths is always the actual
    # page parent.
    assert join_path("/blog@1", "..") == "/"
    assert join_path("/blog@2", "..") == "/"

    # But joins on the same level keep the path
    assert join_path("/blog@1", ".") == "/blog@1"
    assert join_path("/blog@2", ".") == "/blog@2"
    assert join_path("/blog@1", "") == "/blog@1"
    assert join_path("/blog@2", "") == "/blog@2"


def test_is_path_child_of():

    assert not is_path_child_of("a/b", "a/b")
    assert is_path_child_of("a/b", "a/b", strict=False)
    assert is_path_child_of("a/b/c", "a")
    assert not is_path_child_of("a/b/c", "b")
    assert is_path_child_of("a/b@foo/bar", "a/b@foo")
    assert is_path_child_of("a/b@foo", "a/b@foo", strict=False)
    assert not is_path_child_of("a/b@foo/bar", "a/c@foo")
    assert not is_path_child_of("a/b@foo/bar", "a/c")
    assert is_path_child_of("a/b@foo", "a/b")
    assert is_path_child_of("a/b@foo/bar", "a/b@foo")
    assert not is_path_child_of("a/b@foo/bar", "a/b@bar")


def test_magic_split_ext():

    assert magic_split_ext("wow") == ("wow", "")
    assert magic_split_ext("aaa.jpg") == ("aaa", "jpg")
    assert magic_split_ext("aaa. jpg") == ("aaa. jpg", "")
    assert magic_split_ext("aaa.j pg") == ("aaa.j pg", "")
    assert magic_split_ext("aaa.j pg", ext_check=False) == ("aaa", "j pg")


def test_slugify():

    assert slugify("w o w") == "w-o-w"
    assert slugify("Șö prĕtty") == "so-pretty"
    assert slugify("im age.jpg") == "im-age.jpg"
    assert slugify("slashed/slug") == "slashed/slug"


def test_url_builder():

    assert build_url([]) == "/"
    assert build_url(["a", "b/c"]) == "/a/b/c/"
    assert build_url(["a", "b/c"], trailing_slash=False) == "/a/b/c"
    assert build_url(["a", "b/c.html"]) == "/a/b/c.html"
    assert build_url(["a", "b/c.html"], trailing_slash=True) == "/a/b/c.html/"
    assert build_url(["a", None, "b", "", "c"]) == "/a/b/c/"


def test_parse_path():

    assert parse_path("") == []
    assert parse_path("/") == []
    assert parse_path("/foo") == ["foo"]
    assert parse_path("/foo/") == ["foo"]
    assert parse_path("/foo/bar") == ["foo", "bar"]
    assert parse_path("/foo/bar/") == ["foo", "bar"]
    assert parse_path("/foo/bar/../stuff") == ["foo", "bar", "stuff"]


@pytest.mark.parametrize(
    "source, target, expected",
    [
        ("/", "./a/", "a/"),
        ("/", "./a", "a"),
        ("/fr/blog/2015/11/a/", "/fr/blog/2015/11/a/a.jpg", "a.jpg"),
        ("/fr/blog/2015/11/a/", "/fr/blog/", "../../../"),
        ("/fr/blog/2015/11/a.php", "/fr/blog/", "../../"),
        ("/fr/blog/2015/11/a/", "/fr/blog/2016/", "../../../2016/"),
        ("/fr/blog/2015/11/a/", "/fr/blog/2016/c.jpg", "../../../2016/c.jpg"),
        ("/fr/blog/2016/", "/fr/blog/2015/a/", "../2015/a/"),
        ("/fr/blog/2016/", "/fr/blog/2015/a/d.jpg", "../2015/a/d.jpg"),
        ("/fr/blog/2015/11/a/", "/images/b.svg", "../../../../../images/b.svg"),
        ("/fr/blog/", "2015/11/", "2015/11/"),
        ("/fr/blog/x", "2015/11/", "2015/11/"),
        ("", "./a/", "a/"),
        ("", "./a", "a"),
        ("fr/blog/2015/11/a/", "fr/blog/2015/11/a/a.jpg", "a.jpg"),
        ("fr/blog/2015/11/a/", "fr/blog/", "../../../"),
        ("fr/blog/2015/11/a.php", "fr/blog/", "../../"),
        ("fr/blog/2015/11/a/", "fr/blog/2016/", "../../../2016/"),
        ("fr/blog/2015/11/a/", "fr/blog/2016/c.jpg", "../../../2016/c.jpg"),
        ("fr/blog/2016/", "fr/blog/2015/a/", "../2015/a/"),
        ("fr/blog/2016/", "fr/blog/2015/a/d.jpg", "../2015/a/d.jpg"),
        ("fr/blog/2015/11/a/", "images/b.svg", "../../../../../images/b.svg"),
        ("fr/blog/", "2015/11/", "../../2015/11/"),
        ("fr/blog/x", "2015/11/", "../../2015/11/"),
    ],
)
def test_make_relative_url(source, target, expected):
    assert make_relative_url(source, target) == expected


def test_make_relative_url_relative_source_absolute_target():
    with pytest.raises(ValueError):
        make_relative_url("rel/a/tive/", "/abs/o/lute")
