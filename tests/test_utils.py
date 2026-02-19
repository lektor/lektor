import os
import stat
import warnings
from contextlib import contextmanager
from dataclasses import dataclass
from itertools import islice
from pathlib import Path
from urllib.parse import urlsplit

import pytest

from lektor.utils import atomic_open
from lektor.utils import build_url
from lektor.utils import create_temp
from lektor.utils import deprecated
from lektor.utils import is_path_child_of
from lektor.utils import join_path
from lektor.utils import magic_split_ext
from lektor.utils import make_relative_url
from lektor.utils import parse_path
from lektor.utils import secure_url
from lektor.utils import slugify
from lektor.utils import split_camel_case
from lektor.utils import unique_everseen
from lektor.utils import untrusted_to_os_path
from lektor.utils import Url


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
        ("/a", "/", "/"),
        ("/a", "/b", "/b"),
        ("a@b", "/", "/"),
        ("a@b", "/c", "/c"),
        ("a@b", "/c@d", "/c@d"),
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


def test_Url_constructor_deprecated():
    with pytest.deprecated_call():
        Url("https://example.org")


@dataclass
class SampleUrl:
    uri: str
    iri: str

    @property
    def split_uri(self):
        return urlsplit(self.uri)

    @property
    def split_iri(self):
        return urlsplit(self.iri)


SAMPLE_URLS = [
    SampleUrl("https://example.org/foo", "https://example.org/foo"),
    SampleUrl("https://example.org:8001/f%C3%BC", "https://example.org:8001/fü"),
    SampleUrl(
        "https://xn--wgv71a119e.idn.icann.org/%E5%A4%A7",
        "https://日本語.idn.icann.org/大",
    ),
    SampleUrl("/?q=sch%C3%B6n#gru%C3%9F", "/?q=schön#gruß"),
]


@pytest.fixture(params=SAMPLE_URLS, ids=lambda sample: sample.uri)
def sample_url(request):
    sample_url = request.param
    # sanity checks
    assert sample_url.split_uri.scheme == sample_url.split_iri.scheme
    assert sample_url.split_uri.port == sample_url.split_iri.port
    return sample_url


def test_Url_str(sample_url):
    assert str(Url.from_string(sample_url.iri)) == sample_url.iri
    assert str(Url.from_string(sample_url.uri)) == sample_url.uri


def test_Url_ascii_url(sample_url):
    assert Url.from_string(sample_url.iri).ascii_url == sample_url.uri
    assert Url.from_string(sample_url.uri).ascii_url == sample_url.uri


def test_Url_ascii_host(sample_url):
    assert Url.from_string(sample_url.iri).ascii_host == sample_url.split_uri.hostname
    assert Url.from_string(sample_url.uri).ascii_host == sample_url.split_uri.hostname


def test_Url_scheme(sample_url):
    assert Url.from_string(sample_url.iri).scheme == sample_url.split_uri.scheme
    assert Url.from_string(sample_url.uri).scheme == sample_url.split_uri.scheme


def test_Url_host(sample_url):
    assert Url.from_string(sample_url.iri).host == sample_url.split_iri.hostname
    assert Url.from_string(sample_url.uri).host == sample_url.split_iri.hostname


def test_Url_port(sample_url):
    assert Url.from_string(sample_url.iri).port == sample_url.split_uri.port
    assert Url.from_string(sample_url.uri).port == sample_url.split_uri.port


def test_Url_path(sample_url):
    assert Url.from_string(sample_url.iri).path == sample_url.split_iri.path
    assert Url.from_string(sample_url.uri).path == sample_url.split_iri.path


def test_Url_query(sample_url):
    assert Url.from_string(sample_url.iri).query == sample_url.split_iri.query
    assert Url.from_string(sample_url.uri).query == sample_url.split_iri.query


def test_Url_anchor(sample_url):
    assert Url.from_string(sample_url.iri).anchor == sample_url.split_iri.fragment
    assert Url.from_string(sample_url.uri).anchor == sample_url.split_iri.fragment


@pytest.mark.parametrize(
    "url, expected",
    [
        ("https://user:pw@example.org/p", "https://user@example.org/p"),
        ("https://user:pw@example.org:8000", "https://user@example.org:8000"),
        ("https://user@example.org/b", "https://user@example.org/b"),
    ],
)
def test_secure_url(url, expected):
    assert secure_url(url) == expected


@pytest.mark.parametrize(
    "input, expected",
    [
        ("ASeriousNote", ["A", "Serious", "Note"]),
        ("TheIRSNeverSleeps", ["The", "IRS", "Never", "Sleeps"]),
        ("Space Separated", ["Space", "Separated"]),
        (" stripped ", ["stripped"]),
        pytest.param(
            "GrußGott",
            ["Gruß", "Gott"],
            marks=pytest.mark.xfail(reason="does not yet work with non-ascii"),
        ),
    ],
)
def test_split_camel_case(input, expected):
    assert split_camel_case(input) == expected


def test_url_builder():
    assert build_url([]) == "/"
    assert build_url(["a", "b/c"]) == "/a/b/c/"
    assert build_url(["a", "b/c"], trailing_slash=False) == "/a/b/c"
    assert build_url(["a", "b/c.html"]) == "/a/b/c.html"
    assert build_url(["a", "b/c.html"], trailing_slash=True) == "/a/b/c.html/"
    assert build_url(["a", None, "b", "", "c"]) == "/a/b/c/"


def test_url_builder_dot_handling():
    assert build_url(["blog", "01.01.2025", "photos"]) == "/blog/01.01.2025/photos/"


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


def test_atomic_open(tmp_path):
    path = tmp_path / "test.txt"
    path.write_text("previous")

    with atomic_open(path, "w") as fp:
        fp.write("new")
        fp.flush()
        assert path.read_text() == "previous"
        assert len(list(tmp_path.iterdir())) == 2
    assert path.read_text() == "new"
    assert len(list(tmp_path.iterdir())) == 1


def test_atomic_open_exception(tmp_path):
    path = tmp_path / "test.txt"

    with pytest.raises(RuntimeError, match="test"):
        with atomic_open(path, "w") as fp:
            fp.write("new")
            fp.flush()
            raise RuntimeError("test")
    assert len(list(tmp_path.iterdir())) == 0


@pytest.fixture(params=[0o022, 0o002, 0x000])
def umask(request):
    umask = request.param
    if os.name == "nt":
        pytest.skip("Windows does not support umask")
    saved = os.umask(umask)
    try:
        yield umask
    finally:
        os.umask(saved)


def test_atomic_open_respects_umask(tmp_path, umask):
    path = tmp_path / "test.txt"
    with atomic_open(path, "w"):
        pass
    assert oct(stat.S_IMODE(path.stat().st_mode)) == oct(0o666 & ~umask)


@pytest.mark.parametrize("mode", ["a", "w+", "x", "rw", "foo"])
def test_atomic_open_raises_on_bad_mode(tmp_path, mode):
    with pytest.raises(ValueError, match="mode"):
        with atomic_open(tmp_path / "file.txt", mode):
            pass


def test_create_temp(tmp_path):
    assert sum(1 for _ in tmp_path.iterdir()) == 0
    fd, filename = create_temp(prefix="a", suffix=".bin", dir=tmp_path)
    assert sum(1 for _ in tmp_path.iterdir()) == 1
    assert Path(filename).parent == tmp_path
    os.write(fd, b"test\n")
    os.close(fd)
    assert Path(filename).read_bytes() == b"test\n"


@pytest.mark.parametrize("mode", [0o666, 0o777])
def test_create_temp_respects_umask(tmp_path, mode, umask):
    _, filename = create_temp(dir=tmp_path, mode=mode)
    assert oct(stat.S_IMODE(os.stat(filename).st_mode)) == oct(mode & ~umask)


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
    with open(warning.filename, encoding="utf-8") as fp:
        return next(islice(fp, warning.lineno - 1, None), None)


@pytest.mark.parametrize(
    "db_path, expected",
    [
        ("a/b", "a/b"),
        ("/a/b", "a/b"),
        ("a/b/", "a/b"),
        ("/../../a", "a"),
    ],
)
def test_untrusted_to_os_path(db_path, expected):
    os_path = untrusted_to_os_path(db_path)
    assert os_path.split(os.sep) == expected.split("/")
