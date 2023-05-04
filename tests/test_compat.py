import os
from pathlib import Path
from urllib.parse import urlsplit

import pytest
from werkzeug import urls as werkzeug_urls

from lektor.compat import _CompatURL
from lektor.compat import _ensure_tree_writeable
from lektor.compat import FixedTemporaryDirectory
from lektor.compat import TemporaryDirectory


def test_ensure_tree_writeable(tmp_path):
    topdir = tmp_path / "topdir"
    subdir = topdir / "subdir"
    regfile = subdir / "regfile"
    subdir.mkdir(parents=True)
    regfile.touch(mode=0)
    subdir.chmod(0)
    topdir.chmod(0)

    _ensure_tree_writeable(topdir)

    for p in topdir, subdir, regfile:
        assert os.access(p, os.W_OK)


@pytest.mark.parametrize("tmpdir_class", [FixedTemporaryDirectory, TemporaryDirectory])
def test_TemporaryDirectory(tmpdir_class):
    with tmpdir_class() as tmpdir:
        file = Path(tmpdir, "test-file")
        file.touch(mode=0)
        os.chmod(tmpdir, 0)
    assert not os.path.exists(tmpdir)


def make_CompatURL(url: str) -> _CompatURL:
    return _CompatURL._make(urlsplit(url))


URL_MAKERS = [
    pytest.param(make_CompatURL, id="_CompatURL"),
    pytest.param(
        getattr(werkzeug_urls, "url_parse", None),
        id="werkzeug.urls.URL",
        marks=pytest.mark.skipif(
            not hasattr(werkzeug_urls, "url_parse"),
            reason="werkzeug.urls.url_parse is not available",
        ),
    ),
]


@pytest.fixture(params=URL_MAKERS)
def make_url(request):
    return request.param


pytestmark = pytest.mark.filterwarnings("ignore:'werkzeug:DeprecationWarning")


def test_compatURL_replace(make_url):
    url = make_url("http://example.org/foo")
    assert str(url.replace(scheme="https", path="bar")) == "https://example.org/bar"


def test_compatURL_host(make_url):
    assert make_url("http://bücher.example/foo").host == "bücher.example"


@pytest.mark.parametrize(
    "url, expected",
    [
        ("http:/foo", [None]),
        ("http://bücher.example/foo", ["xn--bcher-kva.example"]),
        # werkzeug < 2.3 strips non-ascii
        ("http://bad\uFFFF.example.org", ["bad\uFFFF.example.org", "bad.example.org"]),
    ],
)
def test_compatURL_ascii_host(url, expected, make_url):
    assert make_url(url).ascii_host in expected


def test_compatURL_auth(make_url):
    assert make_url("http://u:p@example.org/").auth == "u:p"


@pytest.mark.parametrize(
    "url, expected",
    [
        ("http://example.org/", None),
        ("http://a%20user@example.org/", "a user"),
        ("http://%C3%BCser:pw@example.org/", "üser"),
        ("http://%FCser:pw@example.org/", "üser"),  # latin1
    ],
)
def test_compatURL_username(url, expected, make_url):
    assert make_url(url).username == expected


def test_compatURL_raw_username(make_url):
    assert make_url("http://a%20user:p@example.org/").raw_username == "a%20user"


@pytest.mark.parametrize(
    "url, expected",
    [
        ("http://user@example.org/", None),
        ("http://user:pass%20word@example.org/", "pass word"),
    ],
)
def test_compatURL_password(url, expected, make_url):
    assert make_url(url).password == expected


def test_compatURL_raw_password(make_url):
    assert make_url("http://u:pass%20word@example.org/").raw_password == "pass%20word"


def test_compatURL_decode_query(make_url):
    args = make_url("?a=b&c").decode_query()
    assert args["a"] == "b"
    assert args["c"] == ""


def test_compatURL_join(make_url):
    base = make_url("http://example.org/top/index.html")
    assert str(base.join("sibling.html")) == "http://example.org/top/sibling.html"


def test_compatURL_join_tuple(make_url):
    base = make_url("http://example.org/top/index.html")
    url = ("", "", "sibling.html", "q", "f")
    assert str(base.join(url)) == "http://example.org/top/sibling.html?q#f"


def test_compatURL_to_url(make_url):
    strval = "http://example.org/foo?q#a"
    url = make_url(strval)
    assert url.to_url() == strval
    assert str(url) == strval


@pytest.mark.filterwarnings("ignore:(?i).*werkzeug:DeprecationWarning")
def test_compatURL_to_uri_tuple(make_url):
    uri_tuple = make_url("http://example.org/fü/").to_uri_tuple()
    assert uri_tuple == ("http", "example.org", "/f%C3%BC/", "", "")


@pytest.mark.filterwarnings("ignore:(?i).*werkzeug:DeprecationWarning")
def test_compatURL_to_iri_tuple(make_url):
    iri_tuple = make_url("http://example.org/f%C3%BC/").to_iri_tuple()
    assert iri_tuple == ("http", "example.org", "/fü/", "", "")
