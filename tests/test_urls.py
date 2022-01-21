import pytest

from lektor.context import _ctx_stack
from lektor.context import Context
from lektor.utils import cleanup_path


def test_cleanup_path():
    assert cleanup_path("/") == "/"
    assert cleanup_path("/foo") == "/foo"
    assert cleanup_path("/foo/") == "/foo"
    assert cleanup_path("/////foo/") == "/foo"
    assert cleanup_path("/////foo////") == "/foo"
    assert cleanup_path("/////foo/.///") == "/foo"
    assert cleanup_path("/////foo/..///") == "/foo"
    assert cleanup_path("/foo/./bar/") == "/foo/bar"
    assert cleanup_path("/foo/../bar/") == "/foo/bar"


@pytest.mark.parametrize(
    "from_path, from_alt, to_path, to_alt, expected",
    [
        ("/projects/wolf", "en", "/projects/slave", "en", "../slave/"),
        ("/projects/wolf", "de", "/projects/slave", "de", "../sklave/"),
        ("/projects/slave", "en", "/projects/slave", "de", "../../de/projects/sklave/"),
        ("/projects/slave", "de", "/projects/slave", "en", "../../../projects/slave/"),
        ("/projects/wolf", "en", "/projects/wolf", "en", "./"),
    ],
)
def test_url_to_page(pad, from_path, from_alt, to_path, to_alt, expected):
    from_ = pad.get(from_path, alt=from_alt)
    to = pad.get(to_path, alt=to_alt)
    assert from_.url_to(to) == expected


@pytest.mark.parametrize(
    "alt, expected",
    [
        ("en", "page/2/"),
        ("de", "../de/blog/page/2/"),
    ],
)
def test_url_to_page_with_explicit_alt(pad, alt, expected):
    page1 = pad.get("/blog", alt="en", page_num=1)
    page2 = pad.get("/blog", alt="en", page_num=2)
    assert page1.url_to(page2, alt=alt) == expected


@pytest.fixture
def mock_build_context(mocker, pad):
    ctx = mocker.Mock(spec=Context, pad=pad)
    _ctx_stack.push(ctx)
    try:
        yield ctx
    finally:
        _ctx_stack.pop()


def test_url_to_thumbnail(pad, mock_build_context):
    extra_de = pad.get("/extra", alt="de")
    thumbnail = pad.get("/test.jpg").thumbnail(42)
    assert extra_de.url_to(thumbnail) == "../../test@42.jpg"


@pytest.mark.parametrize(
    "path, alt, absolute, external, base_url, expected",
    [
        ("/projects/slave", "", None, None, None, "../slave/"),
        ("/projects/slave", "de", None, None, None, "../../de/projects/sklave/"),
        ("/projects/slave", "de", True, None, None, "/de/projects/sklave/"),
        ("/projects/slave", "de", True, True, None, "/de/projects/sklave/"),
        ("/projects/slave", "de", True, True, "/content/", "/de/projects/sklave/"),
        (
            "/projects/slave",
            "de",
            None,
            True,
            None,
            "/projects/slave1/de/projects/sklave/",
        ),
        (
            "/projects/slave",
            "de",
            None,
            True,
            "/content/",
            "/projects/slave1/de/projects/sklave/",
        ),
        ("/projects/slave", "de", None, None, "/content/", "../de/projects/sklave/"),
        ("", "de", None, None, None, "../../de/projects/wolf/"),
        ("!", "de", None, None, None, "./"),
        ("!/projects/slave", "de", None, None, None, "../slave"),
        ("!/projects/slave", None, None, None, None, "../slave"),
        ("!", None, None, None, None, "./"),
        ("", None, None, None, None, "./"),
        ("/projects/slave", None, True, None, None, "/projects/slave/"),
        ("/projects/slave", None, True, True, None, "/projects/slave/"),
        ("/projects/slave", None, True, True, "/content/", "/projects/slave/"),
        ("/projects/slave", None, True, None, "/content/", "/projects/slave/"),
        ("/projects/slave", None, None, True, None, "/projects/slave1/projects/slave/"),
        (
            "/projects/slave",
            None,
            None,
            True,
            "/content/",
            "/projects/slave1/projects/slave/",
        ),
        ("/projects/slave", None, None, None, "/content/", "../projects/slave/"),
        ("/projects/slave", None, None, None, None, "../slave/"),
        # Test relative paths are followed
        ("../../extra", None, None, None, None, "../../extra/"),
        ("../../extra", "de", None, None, None, "../../de/extra/"),
        # No trailing slash
        ("/extra/file.ext", "de", None, None, None, "../../de/extra/file.ext"),
        # Test anchor is preserved
        ("/projects/slave#anchor", None, None, None, None, "../slave/#anchor"),
        # Test explicit alt in query
        ("/projects/slave?alt=de", None, None, None, None, "../../de/projects/sklave/"),
        # Test alt argument to url_to wins over query param
        ("/projects/slave?alt=de", "en", None, None, None, "../slave/"),
        # Unrecognized query params are ignored
        ("/projects/slave?unrecognized=de", None, None, None, None, "../slave/"),
        ("/projects/slave?query#anchor", None, None, None, None, "../slave/#anchor"),
        # Non-resolvable paths are silently treated as URL paths
        ("foo", None, None, None, None, "foo"),
        ("foo?query#anchor", None, None, None, None, "foo?query#anchor"),
        # External urls
        (
            "http://example.org/slave",
            None,
            None,
            None,
            None,
            "http://example.org/slave",
        ),
        ("//example.com/?q#a", None, None, None, None, "//example.com/?q#a"),
        # Test lektor: scheme forces Lektor resolution
        ("lektor:/blog", None, None, None, None, "../../blog/"),
        ("lektor:../coffee", None, None, None, None, "../coffee/"),
    ],
)
def test_url_to_all_params(pad, path, alt, absolute, external, base_url, expected):

    if external and not absolute:
        pad.db.config.base_url = "/projects/slave1/"

    wolf_en = pad.get("/projects/wolf")

    assert wolf_en.url_to(path, alt, absolute, external, base_url) == expected


@pytest.mark.parametrize(
    "path, alt, absolute, external, base_url",
    [
        ("/projects/slave", "de", None, True, None),
        ("/projects/slave", "de", None, True, "/content/"),
        ("/projects/slave", None, None, True, None),
        ("/projects/slave", None, None, True, "/content/"),
        # lektor: scheme forces error if not resolvable via Lektor db
        ("lektor:missing", None, None, True, None),
        # netloc not allow with lektor: scheme
        ("lektor://localhost:5000/blog", None, None, None, None),
    ],
)
def test_url_to_all_params_error_cases(pad, path, alt, absolute, external, base_url):

    wolf_en = pad.get("/projects/wolf")

    with pytest.raises(RuntimeError):
        wolf_en.url_to(path, alt, absolute, external, base_url)


def test_url_parse_virtual_path(pad):
    projects_de = pad.get("/projects@2", alt="de")
    paginated_de = pad.get("/extra/paginated@2", alt="de")
    paginated = pad.get("/extra/paginated@2")
    assert projects_de.url_path == "/de/projects/page/2/"
    assert paginated_de.url_path == "/de/extra/paginiert/page/2/"
    assert paginated.url_path == "/extra/paginated/page/2/"


def test_file_record_url(pad):
    record = pad.get("/extra/file.ext")
    assert record.url_path == "/extra/file.ext"


def test_url_with_slash_slug(pad):
    record = pad.get("/extra/slash-slug")
    assert record.url_path == "/extra/long/path/"
