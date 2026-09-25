import inspect
import os
from pathlib import Path

import pytest

from lektor.project import Project


def test_Project_get_output_path(tmp_path: Path) -> None:
    project_file = tmp_path / "test.lektorproject"
    project_file.touch()
    project = Project.from_file(project_file)
    assert Path(project.get_output_path()).parts[-2:] == ("builds", project.id)


def test_Project_get_output_path_is_relative_to_project_file(tmp_path: Path) -> None:
    tree = tmp_path / "tree"
    tree.mkdir()
    project_file = tmp_path / "test.lektorproject"
    project_file.write_text(
        inspect.cleandoc(
            """[project]
            path = tree
            output_path = htdocs
            """
        )
    )

    project = Project.from_file(project_file)
    assert project.get_output_path() == str(tmp_path / "htdocs")


@pytest.mark.parametrize("path", [None, "rel", "../sibling", "/absolute/path"])
def test_Project_tree(path: str | None, tmp_path: Path) -> None:
    config_dir = tmp_path / "config"
    project_file = config_dir / "test.lektorproject"
    project_file.parent.mkdir(parents=True, exist_ok=True)
    with project_file.open("w") as fp:
        fp.write("[project]\n")
        if path is not None:
            fp.write(f"path = {path}\n")
    project = Project.from_file(project_file)

    assert os.path.normpath(project.tree) == project.tree
    expected = config_dir.joinpath(path).resolve() if path is not None else config_dir
    assert Path(project.tree) == expected
