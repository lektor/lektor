import inspect
import shutil

import pytest

from lektor.project import Project


def write_text(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(inspect.cleandoc(text))


def _fixme(*args):
    return pytest.param(*args, marks=pytest.mark.xfail(reason="FIXME"))


@pytest.fixture(scope="module")
def project_path(tmp_path_factory, data_path):
    """Make our own private copy of the demo-project"""
    demo = data_path / "demo-project"
    path = tmp_path_factory.mktemp("test_serve") / "demo-project"

    shutil.copytree(demo, path)

    write_text(path / "assets/TEST.TXT", "Text file.\n")
    return path


@pytest.fixture
def pad(project_path):
    return Project.from_path(project_path).make_env().new_pad()


@pytest.fixture
def asset(pad, asset_path):
    return pad.get_asset(asset_path)


@pytest.mark.parametrize(
    "asset_path, url_path",
    [
        ("/", "/"),
        ("/static", "/static/"),
        ("/static/demo.css", "/static/demo.css"),
        ("/TEST.TXT", "/TEST.txt"),
    ],
)
def test_asset_url_path(asset, url_path):
    assert asset.url_path == url_path


@pytest.mark.parametrize(
    "asset_path, artifact_name",
    [
        ("/", "/"),
        ("/static", "/static"),
        ("/static/demo.css", "/static/demo.css"),
        ("/TEST.TXT", "/TEST.txt"),
    ],
)
def test_asset_artifact_name(asset, artifact_name):
    assert asset.artifact_name == artifact_name


@pytest.mark.parametrize(
    "asset_path, child_names",
    [
        ("/dir_with_index_html", {"index.html"}),
        ("/static", {"demo.css"}),
        ("/static/demo.css", set()),
    ],
)
def test_asset_children(asset, child_names):
    assert set(child.name for child in asset.children) == child_names


@pytest.mark.parametrize("asset_path", ["/static"])
def test_asset_children_no_children_if_dir_unreadable(asset):
    asset.source_filename += "-missing"
    assert len(set(asset.children)) == 0


@pytest.mark.parametrize(
    "asset_path, name, from_url, child_name",
    [
        ("/", "empty", False, "empty"),
        ("/", "missing", False, None),
        ("/", "foo-prefix-makes-me-excluded", False, None),
        (
            "/",
            "_include_me_despite_underscore",
            False,
            "_include_me_despite_underscore",
        ),
        ("/static", "demo.css", False, "demo.css"),
        ("/static/demo.css", "x", False, None),
        ("/empty", "demo.css", False, None),
        # XXX: The from_url special_file_suffixes logic seems not be be used
    ],
)
def test_asset_get_child(asset, name, from_url, child_name):
    if child_name is None:
        assert asset.get_child(name, from_url) is None
    else:
        assert asset.get_child(name, from_url).name == child_name


@pytest.mark.parametrize(
    "asset_path, url_path, expected",
    [
        ("/", ("static",), "/static"),
        ("/", ("static", "demo.css"), "/static/demo.css"),
        ("/", ("missing", "demo.css"), None),
        ("/", ("foo-prefix-makes-me-excluded",), None),
        ("/", ("foo-prefix-makes-me-excluded", "static"), None),
        ("/static", ("demo.css",), "/static/demo.css"),
        _fixme("/", ("TEST.txt",), "/TEST.txt"),
    ],
)
def test_resolve_url_path(asset, url_path, expected):
    if expected is None:
        assert asset.resolve_url_path(url_path) is None
    else:
        assert asset.resolve_url_path(url_path).artifact_name == expected


@pytest.mark.parametrize(
    "asset_path, expected",
    [
        ("/", "<Directory '/'>"),
        ("/static", "<Directory '/static'>"),
        ("/static/demo.css", "<File '/static/demo.css'>"),
        ("/TEST.TXT", "<File '/TEST.txt'>"),
    ],
)
def test_asset_repr(asset, expected):
    assert repr(asset) == expected
