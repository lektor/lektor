# coding: utf-8
from dataclasses import dataclass
from urllib.parse import urlsplit

import pytest

from lektor.utils import build_url
from lektor.utils import is_path_child_of
from lektor.utils import join_path
from lektor.utils import magic_split_ext
from lektor.utils import make_relative_url
from lektor.utils import parse_path
from lektor.utils import secure_url
from lektor.utils import slugify
from lektor.utils import Url


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
    assert str(Url(sample_url.iri)) == sample_url.iri
    assert str(Url(sample_url.uri)) == sample_url.uri


def test_Url_ascii_url(sample_url):
    assert Url(sample_url.iri).ascii_url == sample_url.uri
    assert Url(sample_url.uri).ascii_url == sample_url.uri


def test_Url_ascii_host(sample_url):
    assert Url(sample_url.iri).ascii_host == sample_url.split_uri.hostname
    assert Url(sample_url.uri).ascii_host == sample_url.split_uri.hostname


def test_Url_scheme(sample_url):
    assert Url(sample_url.iri).scheme == sample_url.split_uri.scheme
    assert Url(sample_url.uri).scheme == sample_url.split_uri.scheme


def test_Url_host(sample_url):
    assert Url(sample_url.iri).host == sample_url.split_iri.hostname
    assert Url(sample_url.uri).host == sample_url.split_iri.hostname


def test_Url_port(sample_url):
    assert Url(sample_url.iri).port == sample_url.split_uri.port
    assert Url(sample_url.uri).port == sample_url.split_uri.port


def test_Url_path(sample_url):
    assert Url(sample_url.iri).path == sample_url.split_iri.path
    assert Url(sample_url.uri).path == sample_url.split_iri.path


def test_Url_query(sample_url):
    try:
        assert Url(sample_url.iri).query == sample_url.split_iri.query
        assert Url(sample_url.uri).query == sample_url.split_iri.query
    except AssertionError:
        # This is the behavior prior to Lektor 3.4.x
        assert Url(sample_url.iri).query == sample_url.split_iri.query
        assert Url(sample_url.uri).query == sample_url.split_uri.query
        pytest.xfail("Url.query is weird in Lektor<3.4")


def test_Url_anchor(sample_url):
    assert Url(sample_url.iri).anchor == sample_url.split_iri.fragment
    assert Url(sample_url.uri).anchor == sample_url.split_iri.fragment


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
