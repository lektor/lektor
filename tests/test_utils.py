import warnings
from contextlib import contextmanager
from itertools import islice

import pytest

from lektor.utils import build_url
from lektor.utils import deprecated
from lektor.utils import is_path_child_of
from lektor.utils import join_path
from lektor.utils import magic_split_ext
from lektor.utils import make_relative_url
from lektor.utils import parse_path
from lektor.utils import slugify
from lektor.utils import unique_everseen


@pytest.mark.parametrize(
    "head, tail, expected",
    [
        ("a", "b", "a/b"),
        ("/a", "b", "/a/b"),
        ("a@b", "c", "a@b/c"),
        ("a@b", "", "a@b"),
        ("a@b", "@c", "a@c"),
        ("a@b/c", "a@b", "a/a@b"),
        #
        ("blog@archive", "2015", "blog@archive/2015"),
        ("blog@archive/2015", "..", "blog@archive"),
        ("blog@archive/2015", "@archive", "blog@archive"),
        ("blog@archive", "..", "blog"),
        ("blog@archive", ".", "blog@archive"),
        ("blog@archive", "", "blog@archive"),
        #
        # special behavior: parent of pagination paths is always the actual
        # page parent.
        ("/blog@1", "..", "/"),
        ("/blog@2", "..", "/"),
        # But joins on the same level keep the path
        ("/blog@1", ".", "/blog@1"),
        ("/blog@2", ".", "/blog@2"),
        ("/blog@1", "", "/blog@1"),
        ("/blog@2", "", "/blog@2"),
    ],
)
def test_join_path(head, tail, expected):
    assert join_path(head, tail) == expected


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
    assert parse_path("/foo/bar/../stuff") == ["foo", "stuff"]


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


@pytest.mark.parametrize(
    "seq, expected",
    [
        (iter(()), ()),
        ((2, 1, 1, 2, 1), (2, 1)),
        ((1, 2, 1, 2, 1), (1, 2)),
    ],
)
def test_unique_everseen(seq, expected):
    assert tuple(unique_everseen(seq)) == expected


@contextmanager
def _local_deprecated_call(match=None):
    """Like pytest.deprecated_call, but also check that all warnings
    are attributed to this file.
    """
    with pytest.deprecated_call(match=match) as warnings:
        yield warnings
    assert all(w.filename == __file__ for w in warnings)


@pytest.mark.parametrize(
    "kwargs, match",
    [
        ({}, r"^'f' is deprecated$"),
        ({"reason": "testing"}, r"^'f' is deprecated \(testing\)$"),
        (
            {"reason": "testing", "version": "1.2.3"},
            r"^'f' is deprecated \(testing\) since version 1.2.3$",
        ),
        ({"name": "oldfunc"}, r"^'oldfunc' is deprecated$"),
    ],
)
def test_deprecated_function(kwargs, match):
    @deprecated(**kwargs)
    def f():
        return 42

    with _local_deprecated_call(match=match):
        assert f() == 42


def test_deprecated_method():
    class Cls:
        @deprecated
        def f(self):  # pylint: disable=no-self-use
            return 42

        @deprecated
        def g(self):
            return self.f()

    with _local_deprecated_call(match=r"^'g' is deprecated$") as warnings:
        assert Cls().g() == 42
    assert len(warnings) == 1


def test_deprecated_classmethod():
    class Cls:
        @classmethod
        @deprecated
        def f(cls):
            return 42

        @classmethod
        @deprecated
        def g(cls):
            return cls.f()

    with _local_deprecated_call(match=r"^'g' is deprecated$") as warnings:
        assert Cls().g() == 42
    assert len([w.message for w in warnings]) == 1


def test_deprecated_raises_type_error():
    with pytest.raises(TypeError):
        deprecated(0)


def test_deprecated_stacklevel():
    @deprecated(stacklevel=2)
    def f():
        return 42

    def g():
        return f()

    with _local_deprecated_call(match=r"^'f' is deprecated$") as warnings:
        assert g() == 42
    assert "assert g() == 42" in _warning_line(warnings[0])


def _warning_line(warning: warnings.WarningMessage) -> str:
    """Get the text of the line for which warning was issued."""
    with open(warning.filename, "r", encoding="utf-8") as fp:
        return next(islice(fp, warning.lineno - 1, None), None)
