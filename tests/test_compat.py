import importlib
import tempfile
from urllib.parse import urlsplit

import pytest
from werkzeug import urls as werkzeug_urls

from lektor.compat import _CompatURL


@pytest.mark.parametrize(
    "name, expected_value, replacement",
    [
        (
            "TemporaryDirectory",
            tempfile.TemporaryDirectory,
            "tempfile.TemporaryDirectory",
        ),
        ("importlib_metadata", importlib.metadata, "importlib.metadata"),
    ],
)
def test_deprecated_attr(name, expected_value, replacement):
    lektor_compat = importlib.import_module("lektor.compat")
    with pytest.deprecated_call(match=f"use {replacement} instead") as warnings:
        value = getattr(lektor_compat, name)
    assert value is expected_value
    assert warnings[0].filename == __file__


def test_missing_attr():
    lektor_compat = importlib.import_module("lektor.compat")
    with pytest.raises(AttributeError):
        lektor_compat.MISSING  # pylint: disable=pointless-statement


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
