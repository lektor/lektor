import inspect
import json
import os
import re
from pathlib import Path

import pytest

from lektor.builder import Builder
from lektor.cli import cli
from lektor.devserver import run_server
from lektor.project import Project
from lektor.publisher import publish


def test_build_abort_in_existing_nonempty_dir(project_cli_runner):
    os.mkdir("build_dir")
    with open("build_dir/test", "w", encoding="utf-8"):
        pass
    result = project_cli_runner.invoke(cli, ["build", "-O", "build_dir"], input="n\n")
    assert "Aborted!" in result.output
    assert result.exit_code == 1


def test_build_continue_in_existing_nonempty_dir(project_cli_runner):
    os.mkdir("build_dir")
    with open("build_dir/test", "w", encoding="utf-8"):
        pass
    result = project_cli_runner.invoke(cli, ["build", "-O", "build_dir"], input="y\n")
    assert "Finished prune" in result.output
    assert result.exit_code == 0


def test_alias(project_cli_runner):
    result = project_cli_runner.invoke(cli, ["pr"])  # short for 'project-info'
    assert result.exit_code == 0
    assert "Name: Demo Project" in result.output


def test_dev_cmd_alias(isolated_cli_runner):
    result = isolated_cli_runner.invoke(cli, ["dev", "s"])  # short for 'shell'
    assert result.exit_code == 2
    assert "Error: Could not automatically discover a project" in result.output


def test_alias_multiple_matches(project_cli_runner):
    result = project_cli_runner.invoke(
        cli, ["p"]
    )  # short for 'project-info' & 'plugins'
    assert result.exit_code == 2
    assert "Error: Too many matches" in result.output


def test_alias_no_matches(project_cli_runner):
    result = project_cli_runner.invoke(cli, ["z"])
    assert result.exit_code == 2
    assert "Error: No such command" in result.output


def test_build_no_project(isolated_cli_runner):
    result = isolated_cli_runner.invoke(cli, ["build"])
    assert result.exit_code == 2
    assert "Could not automatically discover a project" in result.output


def test_build(project_cli_runner):
    result = project_cli_runner.invoke(cli, ["build"])
    assert (
        "files or folders already exist" not in result.output
    )  # No warning on fresh build
    assert result.exit_code == 0
    start_matches = re.findall(r"Started build", result.output)
    assert len(start_matches) == 1
    finish_matches = re.findall(r"Finished build in \d+\.\d{2} sec", result.output)
    assert len(finish_matches) == 1

    # rebuild
    result = project_cli_runner.invoke(cli, ["build"])
    assert (
        "files or folders already exist" not in result.output
    )  # No warning on repeat build
    assert result.exit_code == 0


def test_build_extra_flag(project_cli_runner, mocker):
    mock_builder = mocker.patch("lektor.builder.Builder")
    mock_builder.return_value.build_all.return_value = 0
    result = project_cli_runner.invoke(cli, ["build", "-f", "webpack"])
    assert result.exit_code == 0
    assert mock_builder.call_args[1]["extra_flags"] == ("webpack",)


def test_deploy_extra_flag(project_cli_runner, mocker):
    mock_publish = mocker.patch("lektor.publisher.publish")
    result = project_cli_runner.invoke(cli, ["deploy", "-f", "draft"])
    assert result.exit_code == 0
    assert mock_publish.call_args[1]["extra_flags"] == ("draft",)


@pytest.fixture
def project_info_data(project_cli_runner):
    tree_dir = os.getcwd()
    project = Project.from_path(tree_dir)
    return {
        "name": "Demo Project",
        "project_file": os.path.join(tree_dir, "Website.lektorproject"),
        "tree": tree_dir,
        # punt on computing these independently
        "output_path": project.get_output_path(),
        "package_cache": str(project.get_package_cache_path()),
    }


def test_project_info(project_cli_runner, project_info_data):
    result = project_cli_runner.invoke(cli, ["project-info"])
    for heading, key in [
        ("Name", "name"),
        ("File", "project_file"),
        ("Tree", "tree"),
        ("Output", "output_path"),
        ("Package Cache", "package_cache"),
    ]:
        assert f"{heading}: {project_info_data[key]}\n" in result.stdout


@pytest.mark.parametrize(
    "flag",
    ["--name", "--project-file", "--tree", "--output-path", "--package-cache"],
)
def test_project_info_path_flags(project_cli_runner, flag, project_info_data):
    info_key = flag.lstrip("-").replace("-", "_")
    result = project_cli_runner.invoke(cli, ["project-info", flag])
    assert result.exit_code == 0
    assert result.stdout.rstrip() == project_info_data[info_key]


def test_project_info_json(project_cli_runner):
    project = Project.from_path(os.getcwd())
    result = project_cli_runner.invoke(cli, ["project-info", "--json"])
    assert json.loads(result.stdout) == project.to_json()


@pytest.fixture
def deployable_project_data(scratch_project_data):
    project_file = next(scratch_project_data.glob("*.lektorproject"))
    with project_file.open("a") as fp:
        fp.write(
            inspect.cleandoc(
                """[servers.default]
                name = Default
                target = rsync://example.net/
                """
            )
        )
    return scratch_project_data


@pytest.mark.parametrize(
    "subcommand, to_mock, param_name",
    [
        ("build", Builder, "destination_path"),
        ("clean", Builder, "destination_path"),
        ("deploy", publish, "output_path"),
        ("server", run_server, "output_path"),
    ],
)
def test_build_output_path_relative_to_cwd(
    project_cli_runner,
    deployable_project_data,
    mocker,
    subcommand,
    to_mock,
    param_name,
):
    mock = mocker.patch(f"{to_mock.__module__}.{to_mock.__qualname__}", autospec=True)
    args = [
        f"--project={deployable_project_data}",
        subcommand,
        "--output-path=htdocs",
    ]
    project_cli_runner.invoke(cli, args, input="y\n")

    args, kwargs = mock.call_args
    bound_args = inspect.signature(to_mock).bind(*args, **kwargs).arguments
    output_path = bound_args[param_name]
    assert output_path == str(Path.cwd().resolve() / "htdocs")
