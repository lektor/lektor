import inspect
import os
import shutil

import pytest

from lektor.assets import Directory
from lektor.assets import File
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
    asset._paths = tuple(
        path.with_name(path.name + "-missing") for path in asset._paths
    )
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


fs_ignores_case = all(os.path.exists(fn) for fn in (__file__.upper(), __file__.lower()))
xfail_if_fs_cs = pytest.mark.xfail(
    not fs_ignores_case,
    reason="FIXME: fails on case-sensitive filesystems",
)


@pytest.mark.parametrize(
    "asset_path, url_path, expected",
    [
        ("/", ("static",), "/static"),
        ("/", ("static", "demo.css"), "/static/demo.css"),
        ("/", ("missing", "demo.css"), None),
        ("/", ("foo-prefix-makes-me-excluded",), None),
        ("/", ("foo-prefix-makes-me-excluded", "static"), None),
        ("/static", ("demo.css",), "/static/demo.css"),
        pytest.param("/", ("TEST.txt",), "/TEST.txt", marks=xfail_if_fs_cs),
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
