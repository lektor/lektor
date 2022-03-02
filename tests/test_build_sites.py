"""Go/no-go tests that attempt to build various known Lektor sites."""
import os
import sys
from pathlib import Path
from shutil import which
from subprocess import run

import pytest


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
            (sys.executable, "-m", "lektor", "build", "-O", output_dir),
            cwd=project_dir,
            check=True,
        )

    return build_project


def _not_unbuildable(path):
    # This one is not actually buildable (due to bad page id 'bäd')
    return path.name != "ünicöde-project"


def iter_projects(path=Path.cwd(), maxdepth=2, filter=_not_unbuildable):
    if filter(path) and any(path.glob("*.lektorproject")):
        yield str(path.relative_to(Path.cwd()))

    if maxdepth > 0:
        for subdir in path.iterdir():
            if subdir.is_dir():
                yield from iter_projects(subdir, maxdepth=maxdepth - 1)


@pytest.mark.parametrize("project", iter_projects())
def test_build_project(project, build_project):
    build_project(project)


@pytest.mark.skipif(not which("git"), reason="git not installed")
@pytest.mark.requiresinternet
@pytest.mark.slowtest
def test_build_lektor_website(tmp_path, build_project):
    repo = "https://github.com/lektor/lektor-website.git"
    project_dir = tmp_path / "project"

    run(("git", "clone", "--depth=1", repo, project_dir), check=True)
    build_project(project_dir)
