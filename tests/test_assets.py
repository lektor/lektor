import inspect
import shutil
from pathlib import Path

import pytest

from lektor.assets import Directory
from lektor.assets import File
from lektor.assets import get_asset
from lektor.assets import get_asset_root
from lektor.project import Project


def write_text(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(inspect.cleandoc(text))


@pytest.fixture(scope="module")
def project_path(tmp_path_factory, data_path):
    """Make our own private copy of the demo-project"""
    demo = data_path / "demo-project"
    path = tmp_path_factory.mktemp("test_serve") / "demo-project"

    shutil.copytree(demo, path)

    write_text(path / "assets/TEST.TXT", "Text file.\n")
    return path


@pytest.fixture
def pad(project_path, save_sys_path):
    return Project.from_path(project_path).make_env().new_pad()


@pytest.fixture(params=["/", "/static", "/static/demo.css", "/TEST.TXT"])
def asset_path(request):
    return request.param


@pytest.fixture
def asset(pad, asset_path):
    return pad.get_asset(asset_path)


@pytest.mark.parametrize(
    "parent_path, child_name",
    [
        (None, "static"),
        ("/static", "demo.css"),
    ],
)
def test_get_asset(pad, parent_path, child_name):
    parent = pad.get_asset(parent_path) if parent_path is not None else None
    with pytest.deprecated_call(match=r"\bget_asset\b.*\bdeprecated\b") as warnings:
        assert get_asset(pad, child_name, parent=parent).name == child_name
    assert all(warning.filename == __file__ for warning in warnings)


def test_asset_source_filename(asset, pad, asset_path):
    expected = Path(pad.env.root_path, "assets", asset_path.lstrip("/"))
    assert asset.source_filename == str(expected)


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
    "asset_path, expected",
    [
        ("/", "/"),
        ("/static", "/static/"),
        ("/static/demo.css", None),
        ("/TEST.TXT", None),
    ],
)
def test_asset_url_content_path(asset, expected):
    assert asset.url_content_path == expected


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
    assert {child.name for child in asset.children} == child_names


@pytest.mark.parametrize("asset_path", ["/static"])
def test_asset_children_no_children_if_dir_unreadable(asset):
    asset._paths = tuple(
        path.with_name(path.name + "-missing") for path in asset._paths
    )
    assert len(set(asset.children)) == 0


@pytest.mark.parametrize(
    "asset_path, name, child_name",
    [
        ("/", "empty", "empty"),
        ("/", "missing", None),
        ("/", "foo-prefix-makes-me-excluded", None),
        (
            "/",
            "_include_me_despite_underscore",
            "_include_me_despite_underscore",
        ),
        ("/static", "demo.css", "demo.css"),
        ("/static/demo.css", "x", None),
        ("/empty", "demo.css", None),
        # Invalid child names
        ("/static", ".", None),
        ("/", "", None),
    ],
)
def test_asset_get_child(asset, name, child_name):
    if child_name is None:
        assert asset.get_child(name) is None
    else:
        assert asset.get_child(name).name == child_name


def test_asset_get_child_from_url_param_deprecated(asset):
    with pytest.deprecated_call(match=r"\bfrom_url\b.*\bignored\b") as warnings:
        asset.get_child("name", from_url=True)
    assert all(warning.filename == __file__ for warning in warnings)


@pytest.mark.parametrize(
    "asset_path, url_path, expected",
    [
        ("/", ("static",), "/static"),
        ("/", ("static", "demo.css"), "/static/demo.css"),
        ("/", ("static", "demo.css", "parent-not-a-dir"), None),
        ("/", ("missing", "demo.css"), None),
        ("/", ("foo-prefix-makes-me-excluded",), None),
        ("/", ("foo-prefix-makes-me-excluded", "static"), None),
        ("/static", ("demo.css",), "/static/demo.css"),
        ("/", ("TEST.txt",), "/TEST.txt"),
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


@pytest.fixture
def asset_paths(tmp_path):
    paths = tmp_path / "assets1", tmp_path / "assets2"
    for path in paths:
        path.mkdir()
    return paths


@pytest.fixture
def asset_root(pad, asset_paths):
    return get_asset_root(pad, asset_paths)


def test_directory_merges_subdirectories(asset_root, asset_paths):
    for n, path in enumerate(asset_paths):
        subdir = path / "subdir"
        subdir.mkdir()
        subdir.joinpath(f"file{n}").touch()

    subdir_asset = asset_root.get_child("subdir")
    child_names = [child.name for child in subdir_asset.children]
    child_names.sort()
    assert child_names == ["file0", "file1"]


def test_directory_file_shadows_directory(asset_root, asset_paths):
    for n, path in enumerate(asset_paths):
        child_path = path / "child"
        if n == 0:
            child_path.touch()
        else:
            child_path.mkdir()

    children = list(asset_root.children)
    assert len(children) == 1
    assert isinstance(children[0], File)
    assert children[0].name == "child"


def test_directory_directory_conflicts_with_file(asset_root, asset_paths):
    for n, path in enumerate(asset_paths):
        child_path = path / "child"
        if n == 0:
            child_path.mkdir()
        else:
            child_path.touch()

    children = list(asset_root.children)
    assert len(children) == 1
    assert all(isinstance(child, Directory) for child in children)
