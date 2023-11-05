import re

import pytest

from lektor.context import Context
from lektor.environment import Environment
from lektor.reporter import BufferReporter
from lektor.sourceobj import VirtualSourceObject
from lektor.utils import cleanup_path
from lektor.utils import cleanup_url_path

# noreorder
from conftest import restore_import_state  # pylint: disable=wrong-import-order


@pytest.fixture(scope="module")
def pad(project):
    # Use a module-scoped pad to speed tests
    with restore_import_state():
        return Environment(project).new_pad()


@pytest.fixture
def config(pad, monkeypatch):
    """Patch a function-scoped config into our session-scoped pad.

    (For those tests/fixtures that want to mangle the config.)
    """
    config = pad.db.env.load_config()
    monkeypatch.setattr(pad.db, "config", config)
    return config


@pytest.mark.parametrize(
    "path, expected",
    [
        ("", "/"),
        ("/", "/"),
        ("/foo", "/foo"),
        ("//foo", "/foo"),
        ("///foo", "/foo"),
        ("/foo/", "/foo"),
        ("/////foo/", "/foo"),
        ("/////foo////", "/foo"),
        ("/////foo/.///", "/foo"),
        ("/////foo/..///", "/"),
        (".", "/"),
        ("/foo/./bar/", "/foo/bar"),
        ("/foo/../bar/", "/bar"),
    ],
)
def test_cleanup_path(path, expected):
    assert cleanup_path(path) == expected


@pytest.mark.parametrize(
    "url_path, expected",
    [
        ("", "/"),
        ("foo", "/foo"),
        ("foo/", "/foo"),
        ("/", "/"),
        ("//", "/"),
        ("/foo", "/foo"),
        ("/foo/", "/foo"),
        ("///foo", "/foo"),
        ("////foo", "/foo"),
        ("/////foo", "/foo"),
        ("foo///bar", "/foo/bar"),
        ("./foo/.", "/foo"),
        ("/foo/./bar", "/foo/bar"),
        ("../foo", "/foo"),
        ("/../foo/", "/foo"),
        ("foo/../bar", "/bar"),
        ("foo/../../bar/", "/bar"),
        ("foo#frag", "/foo"),  # fragment gets stripped
        ("/foo?query", "/foo"),  # query get stripped
        ("///foo", "/foo"),  # empty netloc
        ("http:foo", "/foo"),  # explicit scheme
        ("HTTP:FOO", "/FOO"),  # explicit scheme get case normalized
        ("https:///foo", "/foo"),  # explicit scheme
    ],
)
def test_cleanup_url_path(url_path, expected):
    assert cleanup_url_path(url_path) == expected


@pytest.mark.parametrize(
    "url_path",
    [
        "file:///foo",  # bad scheme
        "//example.net/bar",  # netloc not allowed
    ],
)
def test_cleanup_url_path_raises_value_error(url_path):
    with pytest.raises(ValueError):
        cleanup_url_path(url_path)


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
def build_context(builder):
    build_state = builder.new_build_state()
    with Context(build_state.new_artifact("dummy-artifact")) as ctx:
        yield ctx


@pytest.mark.usefixtures("build_context")
def test_url_to_thumbnail(pad):
    extra_de = pad.get("/extra", alt="de")
    thumbnail = pad.get("/test.jpg").thumbnail(42)
    assert extra_de.url_to(thumbnail) == "../../test@42x56.jpg"


@pytest.fixture
def external_url(config):
    config.values["PROJECT"]["url"] = "http://example.org/site/"


@pytest.mark.parametrize(
    "path, kwargs, expected",
    [
        ("/projects/slave", {}, "../slave/"),
        ("/projects/slave", {"absolute": True}, "/site/projects/slave/"),
        (
            "/projects/slave",
            {"external": True},
            "http://example.org/site/projects/slave/",
        ),
        (
            "/projects/slave",
            {"absolute": True, "external": True},
            "/site/projects/slave/",
        ),
    ],
)
@pytest.mark.usefixtures("external_url")
def test_url_to_external(pad, path, kwargs, expected):
    wolf_en = pad.get("/projects/wolf")
    assert wolf_en.url_to(path, **kwargs) == expected


NO_PROJECT_URL = RuntimeError(r"To use absolute.*configure.*URL")
CAN_NOT_RESOLVE = RuntimeError(r"Can not resolve")
NETLOC_NOT_ALLOWED = RuntimeError(r"Netloc not allowed")
CONFLICTING_ALT = RuntimeError(r"Conflicting.*alt")
RESOLVE_INCOMPATIBLE_WITH_BANG = RuntimeError(r"Resolve=True.*incompatible.*!")


def _id_for_dict(value):
    if isinstance(value, dict):
        return ",".join(f"{k}={v!r}" for k, v in value.items())
    return None


@pytest.mark.parametrize(
    "path, kwargs, expected",
    [
        ("", {}, "./"),
        (".", {}, "./"),
        ("./", {}, "./"),
        ("../", {}, "../"),
        ("../wolf", {}, "./"),
        ("../wolf/", {}, "./"),
        ("../wolf/.", {}, "./"),
        ("../slave", {}, "../slave/"),
        ("../wolf/../slave/", {}, "../slave/"),
        ("/", {}, "../../"),
        ("/extra", {}, "../../extra/"),
        ("/projects/wolf", {}, "./"),
        ("/projects/slave", {}, "../slave/"),
        # Test alt
        (".", {"alt": "de"}, "../../de/projects/wolf/"),
        ("../slave", {"alt": "de"}, "../../de/projects/sklave/"),
        ("/projects/wolf", {"alt": "de"}, "../../de/projects/wolf/"),
        ("/projects/slave", {"alt": "de"}, "../../de/projects/sklave/"),
        (".", {"alt": ""}, "./"),
        # Test absolute
        (".", {"absolute": True}, "/projects/wolf/"),
        ("/projects/wolf", {"absolute": True}, "/projects/wolf/"),
        ("../slave", {"absolute": True}, "/projects/slave/"),
        ("/projects/slave", {"absolute": True}, "/projects/slave/"),
        ("../slave", {"alt": "de", "absolute": True}, "/de/projects/sklave/"),
        ("/projects/slave", {"alt": "de", "absolute": True}, "/de/projects/sklave/"),
        # Test external
        # Error if external set and no project URL
        (".", {"external": True}, NO_PROJECT_URL),
        (".", {"external": True, "base_url": "/content/"}, NO_PROJECT_URL),
        ("/projects/slave", {"alt": "de", "external": True}, NO_PROJECT_URL),
        # External ignored if absolute is set
        (".", {"absolute": True, "external": True}, "/projects/wolf/"),
        (
            ".",
            {"absolute": True, "external": True, "base_url": "/content/"},
            "/projects/wolf/",
        ),
        # Test base_url
        (".", {"base_url": "/"}, "projects/wolf/"),
        (".", {"alt": "de", "base_url": "/"}, "de/projects/wolf/"),
        (".", {"base_url": "/content/"}, "../projects/wolf/"),
        (".", {"absolute": True, "base_url": "/content/"}, "/projects/wolf/"),
        # No trailing slash
        ("/extra/file.ext", {}, "../../extra/file.ext"),
        ("/extra/file.ext", {"alt": "de", "absolute": True}, "/de/extra/file.ext"),
        # Custom slug
        ("/extra/slash-slug", {}, "../../extra/long/path/"),
        # Non-resolvable paths are silently treated as URL paths
        ("missing", {}, "missing"),
        ("./missing", {}, "missing"),
        ("../missing", {}, "../missing"),
        ("/missing", {}, "../../missing"),
        ("missing", {"alt": "de"}, "missing"),
        ("../missing", {"alt": "de"}, "../missing"),
        ("missing", {"absolute": True}, "/projects/wolf/missing"),
        ("missing", {"external": True}, NO_PROJECT_URL),
        ("missing", {"base_url": "/projects/"}, "wolf/missing"),
        # Disable resolution with '!' prefix
        ("!missing", {}, "missing"),
        ("!/extra/slash-slug", {}, "../../extra/slash-slug"),
        ("!", {}, "./"),
        ("!.", {}, "."),
        ("!../slave", {}, "../slave"),  # no trailing slash
        ("!../slave", {"alt": "de"}, "../slave"),  # alt ignored
        ("!/projects/slave", {}, "../slave"),
        ("!../slave", {"absolute": True}, "/projects/slave"),
        ("!../slave", {"external": True}, NO_PROJECT_URL),
        ("!../slave", {"absolute": True, "external": True}, "/projects/slave"),
        ("!../slave", {"base_url": "/"}, "projects/slave"),
        # Non-resolvable page falls back to URL-path resolution
        # With full outer product of resolve and strict_resolve options
        ("missing", {}, "missing"),
        ("missing", {"resolve": True}, "missing"),
        ("missing", {"resolve": False}, "missing"),
        ("missing", {"strict_resolve": False}, "missing"),
        ("missing", {"strict_resolve": True}, CAN_NOT_RESOLVE),
        ("missing", {"resolve": True, "strict_resolve": False}, "missing"),
        ("missing", {"resolve": True, "strict_resolve": True}, CAN_NOT_RESOLVE),
        ("missing", {"resolve": False, "strict_resolve": False}, "missing"),
        ("missing", {"resolve": False, "strict_resolve": True}, "missing"),
        # Resolve=True can not be used with '!' prefix
        ("!missing", {"resolve": True}, RESOLVE_INCOMPATIBLE_WITH_BANG),
        ("!missing", {"resolve": False}, "missing"),
        ("!missing", {"strict_resolve": True}, RESOLVE_INCOMPATIBLE_WITH_BANG),
        ("!missing", {"strict_resolve": False}, "missing"),
        ("!missing", {"resolve": False, "strict_resolve": True}, "missing"),
        # Resolvable page with full outer product of resolve and strict_resolve options
        ("/extra/slash-slug", {}, "../../extra/long/path/"),
        ("/extra/slash-slug", {"resolve": True}, "../../extra/long/path/"),
        ("/extra/slash-slug", {"resolve": False}, "../../extra/slash-slug"),
        ("/extra/slash-slug", {"strict_resolve": False}, "../../extra/long/path/"),
        ("/extra/slash-slug", {"strict_resolve": True}, "../../extra/long/path/"),
        (
            "/extra/slash-slug",
            {"resolve": True, "strict_resolve": False},
            "../../extra/long/path/",
        ),
        (
            "/extra/slash-slug",
            {"resolve": True, "strict_resolve": True},
            "../../extra/long/path/",
        ),
        (
            "/extra/slash-slug",
            {"resolve": False, "strict_resolve": False},
            "../../extra/slash-slug",
        ),
        (
            "/extra/slash-slug",
            {"resolve": False, "strict_resolve": True},
            "../../extra/slash-slug",
        ),
        # Alt ignored when resolve=False
        ("../slave", {"alt": "de", "resolve": False}, "../slave"),
        ("../slave", {"alt": "de", "resolve": True}, "../../de/projects/sklave/"),
        # Test anchor is preserved
        ("/projects/slave#anchor", {}, "../slave/#anchor"),
        ("missing#anchor", {}, "missing#anchor"),
        ("!missing#anchor", {}, "missing#anchor"),
        ("/extra#anchor", {"resolve": False}, "../../extra#anchor"),
        # Test anchor is preserved for non-resolved urls
        ("missing?q", {}, "missing?q"),
        ("!missing?q", {}, "missing?q"),
        ("/extra?q", {"resolve": False}, "../../extra?q"),
        # Test query and anchor are preserved for non-resolved urls
        ("missing?q#a", {}, "missing?q#a"),
        ("!missing?q#a", {}, "missing?q#a"),
        ("/extra?q#a", {"resolve": False}, "../../extra?q#a"),
        # Test explicit alt in query
        ("../slave?alt=de", {}, "../../de/projects/sklave/"),
        ("/extra?alt=de", {}, "../../de/extra/"),
        # Conflicting specifications for alt
        ("../slave?alt=de", {"alt": "en"}, CONFLICTING_ALT),
        # Unrecognized query params are discarded for resolved urls
        ("../slave?unrecognized=de", {}, "../slave/"),
        ("/extra?query#anchor", {}, "../../extra/#anchor"),
        # External urls
        ("http://example.org/slave", {}, "http://example.org/slave"),
        ("//example.com/?q#a", {}, "//example.com/?q#a"),
        ("some-scheme:foo", {}, "some-scheme:foo"),
    ],
    ids=_id_for_dict,
)
def test_url_to_all_params(pad, path, kwargs, expected):
    wolf_en = pad.get("/projects/wolf")
    if isinstance(expected, Exception):
        with pytest.raises(type(expected)) as exc_info:
            wolf_en.url_to(path, **kwargs)
        assert re.search(str(expected), str(exc_info.value))
    else:
        assert wolf_en.url_to(path, **kwargs) == expected


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


class DummyVirtualSource(VirtualSourceObject):
    url_path = None  # mask inherited property

    def __init__(self, record, url_path):
        super().__init__(record)
        self.url_path = url_path

    @property
    def url_content_path(self):
        # This is a url_content_path that is appropriate for a
        # source object that can contain other child source objects
        if self.url_path.endswith("/"):
            return self.url_path
        head, sep, tail = self.url_path.rpartition("/")
        return f"{head}{sep}_{tail}/"

    @property
    def path(self):
        return f"{self.record.path}@virtual"


@pytest.mark.parametrize(
    "path, url_path, expected",
    [
        ("/", "/path/virtual/", "../../"),
        ("/index.html", "/path/virtual/", "../../index.html"),
        ("rel", "/path/virtual/", "rel"),
        ("rel", "/path/virtual.html", "_virtual.html/rel"),
    ],
)
def test_url_from_virtual(pad, path, url_path, expected):
    virtual = DummyVirtualSource(pad.get("/extra"), url_path)
    assert virtual.url_to(path) == expected


@pytest.mark.parametrize(
    "path, expected",
    [
        ("a", "_file.ext/a"),
        ("/", "../"),
        ("/projects", "../projects/"),
    ],
)
def test_url_from_page_with_dotted_name(pad, path, expected):
    record = pad.get("/extra/file.ext")
    assert record.url_to(path) == expected


@pytest.mark.parametrize(
    "path, expected",
    [
        ("a", "a"),
        ("/", "../"),
        ("/projects", "../projects/"),
    ],
)
def test_url_from_attachment(pad, path, expected):
    record = pad.get("/extra/hello.txt")
    assert record.url_to(path) == expected


def test_url_from_attachment_issues_warning(pad):
    record = pad.get("/extra/hello.txt")
    with BufferReporter(pad.env) as reporter:
        assert record.url_to("a") == "a"
    message = next(filter(None, (extra.get("message") for _, extra in reporter.buffer)))
    assert re.match(r"(?i)Suspicious use of relative URL", message)
