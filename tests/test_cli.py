import os
import re
import warnings

import pytest
from markers import imagemagick

from lektor.cli import cli
from lektor.project import Project


def test_build_abort_in_existing_nonempty_dir(project_cli_runner):
    os.mkdir("build_dir")
    with open("build_dir/test", "w", encoding="utf-8"):
        pass
    result = project_cli_runner.invoke(cli, ["build", "-O", "build_dir"], input="n\n")
    assert "Aborted!" in result.output
    assert result.exit_code == 1


@imagemagick
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
    result = isolated_cli_runner.invoke(cli, ["dev", "p"])  # short for 'publish-plugin'
    assert result.exit_code == 2
    assert "Error: This command must be run in a Lektor plugin folder" in result.output


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
    assert "Could not automatically discover project." in result.output


@imagemagick
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
    assert "use --extra-flag instead of --build-flag" not in result.output


def test_deprecated_build_flag(project_cli_runner, mocker):
    mock_builder = mocker.patch("lektor.builder.Builder")
    mock_builder.return_value.build_all.return_value = 0
    with warnings.catch_warnings(record=True) as w:
        result = project_cli_runner.invoke(cli, ["build", "--build-flag", "webpack"])
        assert result.exit_code == 0
        assert mock_builder.call_args[1]["extra_flags"] == ("webpack",)
        assert w
        assert "use --extra-flag instead of --build-flag" in str(w[0].message)


def test_deploy_extra_flag(project_cli_runner, mocker):
    mock_publish = mocker.patch("lektor.publisher.publish")
    result = project_cli_runner.invoke(cli, ["deploy", "-f", "draft"])
    assert result.exit_code == 0
    assert mock_publish.call_args[1]["extra_flags"] == ("draft",)


@pytest.mark.parametrize(
    "flag, expect",
    [
        ("--name", "Demo Project"),
        ("--project-file", "{tree_dir}{os.sep}Website.lektorproject"),
        ("--tree", "{tree_dir}"),
        ("--output-path", "{output_path}"),
    ],
)
def test_project_info_path_flags(project_cli_runner, flag, expect):
    tree_dir = os.getcwd()
    result = project_cli_runner.invoke(cli, ["project-info", flag])
    assert result.exit_code == 0
    assert result.stdout.rstrip() == expect.format(
        tree_dir=tree_dir,
        output_path=Project.from_path(tree_dir).get_output_path(),
        os=os,
    )
