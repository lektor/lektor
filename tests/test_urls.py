import pytest

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


def test_basic_url_to_with_alts(pad):

    wolf_en = pad.get("/projects/wolf", alt="en")
    slave_en = pad.get("/projects/slave", alt="en")
    wolf_de = pad.get("/projects/wolf", alt="de")
    slave_de = pad.get("/projects/slave", alt="de")

    assert wolf_en.url_to(slave_en) == "../slave/"
    assert wolf_de.url_to(slave_de) == "../sklave/"
    assert slave_en.url_to(slave_de) == "../../de/projects/sklave/"
    assert slave_de.url_to(slave_en) == "../../../projects/slave/"


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
