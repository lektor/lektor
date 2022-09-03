"""Go/no-go tests that attempt to build various known Lektor sites."""
import os
import sys
from pathlib import Path
from shutil import which
from subprocess import run

import pytest
from markers import imagemagick


@pytest.fixture(autouse=True)
def with_temporary_lektor_cache(tmp_path_factory, monkeypatch):
    # Don't pollute user's lektor cache
    cache_dir = tmp_path_factory.mktemp("cache")
    for key in "XDG_CACHE_HOME", "LOCALAPPDATA":
        monkeypatch.setitem(os.environ, key, str(cache_dir))


@pytest.fixture
def build_project(tmp_path):
    output_dir = tmp_path / "output"

    def build_project(project_dir):
        run(
            (sys.executable, "-m", "lektor", "build", "-O", output_dir.__fspath__()),
            cwd=project_dir,
            check=True,
        )

    return build_project


requires_ffmpeg = pytest.mark.skipif(
    not all(which(_) for _ in ("ffmpeg", "ffprobe")),
    reason="requires ffmpeg and ffprobe",
)


@pytest.mark.parametrize(
    "project",
    [
        "tests/child-sources-test-project",
        "tests/dependency-test-project",
        pytest.param("example", marks=imagemagick),
        pytest.param("tests/demo-project", marks=(imagemagick, requires_ffmpeg)),
    ],
)
def test_build_project(project, build_project):
    project_path = Path(__file__).parent.parent / project
    build_project(project_path)


@pytest.mark.skipif(not which("git"), reason="git not installed")
@pytest.mark.requiresinternet
@pytest.mark.slowtest
@imagemagick
def test_build_lektor_website(tmp_path, build_project):
    repo = "https://github.com/lektor/lektor-website.git"
    project_dir = tmp_path / "project"

    run(("git", "clone", "--depth=1", repo, project_dir.__fspath__()), check=True)
    build_project(project_dir)
