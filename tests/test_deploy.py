import textwrap
from os.path import dirname
from os.path import join

import pytest
from werkzeug.urls import url_parse

from lektor.publisher import GithubPagesPublisher
from lektor.publisher import RsyncPublisher


def test_get_server(env):
    server = env.load_config().get_server("production")
    assert server.name == "Production"
    assert server.name_i18n["de"] == "Produktion"
    assert server.target == "rsync://myserver.com/path/to/website"
    assert server.extra == {"extra_field": "extra_value"}


def test_ghpages_update_git_config(tmpdir, env):
    output_path = tmpdir.mkdir("output")
    publisher = GithubPagesPublisher(env, str(output_path))
    repo_path = tmpdir.mkdir("repo")
    repo_config = repo_path.mkdir(".git").join("config").ensure(file=True)
    target_url = url_parse("ghpages://user/repo")
    branch = "master"
    publisher.update_git_config(str(repo_path), target_url, branch)
    expected = textwrap.dedent(
        """
        [remote "origin"]
        url = git@github.com:user/repo.git
        fetch = +refs/heads/master:refs/remotes/origin/master
    """
    ).strip()
    assert repo_config.read().strip() == expected


def test_ghpages_update_git_config_https(tmpdir, env):
    output_path = tmpdir.mkdir("output")
    publisher = GithubPagesPublisher(env, str(output_path))
    repo_path = tmpdir.mkdir("repo")
    repo_config = repo_path.mkdir(".git").join("config").ensure(file=True)
    target_url = url_parse("ghpages+https://pybee/pybee.github.io?cname=pybee.org")
    branch = "lektor"
    publisher.update_git_config(str(repo_path), target_url, branch)
    expected = textwrap.dedent(
        """
        [remote "origin"]
        url = https://github.com/pybee/pybee.github.io.git
        fetch = +refs/heads/lektor:refs/remotes/origin/lektor
    """
    ).strip()
    assert repo_config.read().strip() == expected


def test_ghpages_update_git_config_https_credentials(tmpdir, env):
    output_path = tmpdir.mkdir("output")
    publisher = GithubPagesPublisher(env, str(output_path))
    repo_path = tmpdir.mkdir("repo")
    repo_config = repo_path.mkdir(".git").join("config").ensure(file=True)
    target_url = url_parse("ghpages+https://pybee/pybee.github.io?cname=pybee.org")
    branch = "lektor"
    credentials_file = repo_path.join(".git", "credentials")
    credentials = {
        "username": "fakeuser",
        "password": "fakepass",
    }
    publisher.update_git_config(
        str(repo_path), target_url, branch, credentials=credentials
    )
    expected = (
        textwrap.dedent(
            """
        [remote "origin"]
        url = https://github.com/pybee/pybee.github.io.git
        fetch = +refs/heads/lektor:refs/remotes/origin/lektor
        [credential]
        helper = store --file "{}"
    """
        )
        .format(credentials_file)
        .strip()
    )
    assert repo_config.read().strip() == expected

    assert (
        credentials_file.read().strip()
        == "https://fakeuser:fakepass@github.com".strip()
    )


def test_ghpages_write_cname(tmpdir, env):
    output_path = tmpdir.mkdir("output")
    publisher = GithubPagesPublisher(env, str(output_path))
    target_url = url_parse("ghpages+https://pybee/pybee.github.io?cname=pybee.org")
    publisher.write_cname(str(output_path), target_url)
    assert (output_path / "CNAME").read() == "pybee.org\n"


def test_ghpages_detect_branch_username(tmpdir, env):
    output_path = tmpdir.mkdir("output")
    publisher = GithubPagesPublisher(env, str(output_path))
    target_url = url_parse("ghpages+https://MacDownApp/MacDownApp.github.io")
    branch = publisher.detect_target_branch(target_url)
    assert branch == "master"


def test_ghpages_detect_branch_username_case_insensitive(tmpdir, env):
    output_path = tmpdir.mkdir("output")
    publisher = GithubPagesPublisher(env, str(output_path))
    target_url = url_parse("ghpages+https://MacDownApp/macdownapp.github.io")
    branch = publisher.detect_target_branch(target_url)
    assert branch == "master"


def test_ghpages_detect_branch_project(tmpdir, env):
    output_path = tmpdir.mkdir("output")
    publisher = GithubPagesPublisher(env, str(output_path))
    target_url = url_parse("ghpages+https://MacDownApp/MacDownApp.github.io/macdown")
    branch = publisher.detect_target_branch(target_url)
    assert branch == "gh-pages"


def test_rsync_command_credentials(tmpdir, mocker, env):
    output_path = tmpdir.mkdir("output")
    publisher = RsyncPublisher(env, str(output_path))
    target_url = url_parse("http://example.com")
    ssh_path = tmpdir.mkdir("ssh")
    credentials = {
        "username": "fakeuser",
        "password": "fakepass",
    }
    mock_popen = mocker.patch("lektor.publisher.portable_popen")
    publisher.get_command(target_url, str(ssh_path), credentials)
    assert mock_popen.called
    assert mock_popen.call_args[0] == (
        [
            "rsync",
            "-rclzv",
            "--exclude=.lektor",
            str(output_path) + "/",
            "fakeuser@example.com:/",
        ],
    )


output_path = join(dirname(__file__), "OUTPUT_PATH")


@pytest.mark.parametrize(
    "target_url,called_command",
    [
        (
            "http://example.com",
            [
                "rsync",
                "-rclzv",
                "--exclude=.lektor",
                str(output_path) + "/",
                "example.com:/",
            ],
        ),
        (
            "http://fakeuser@example.com",
            [
                "rsync",
                "-rclzv",
                "--exclude=.lektor",
                str(output_path) + "/",
                "fakeuser@example.com:/",
            ],
        ),
        (
            "http://example.com?exclude=file",
            [
                "rsync",
                "-rclzv",
                "--exclude=.lektor",
                "--exclude",
                "file",
                str(output_path) + "/",
                "example.com:/",
            ],
        ),
        (
            "http://example.com?exclude=file_one&exclude=file_two",
            [
                "rsync",
                "-rclzv",
                "--exclude=.lektor",
                "--exclude",
                "file_one",
                "--exclude",
                "file_two",
                str(output_path) + "/",
                "example.com:/",
            ],
        ),
        (
            """http://example.com?exclude='user's "special" file name'""",
            [
                "rsync",
                "-rclzv",
                "--exclude=.lektor",
                "--exclude",
                "'user's \"special\" file name'",
                str(output_path) + "/",
                "example.com:/",
            ],
        ),
        (
            'http://example.com?exclude="file name"',
            [
                "rsync",
                "-rclzv",
                "--exclude=.lektor",
                "--exclude",
                '"file name"',
                str(output_path) + "/",
                "example.com:/",
            ],
        ),
        (
            "http://example.com?delete",
            [
                "rsync",
                "-rclzv",
                "--exclude=.lektor",
                "--delete-after",
                str(output_path) + "/",
                "example.com:/",
            ],
        ),
        (
            "http://example.com?delete=yes",
            [
                "rsync",
                "-rclzv",
                "--exclude=.lektor",
                "--delete-after",
                str(output_path) + "/",
                "example.com:/",
            ],
        ),
        (
            "http://example.com?delete=no",
            [
                "rsync",
                "-rclzv",
                "--exclude=.lektor",
                str(output_path) + "/",
                "example.com:/",
            ],
        ),
        (
            "file:///path/to/directory",
            [
                "rsync",
                "-rclzv",
                "--exclude=.lektor",
                str(output_path) + "/",
                "/path/to/directory/",
            ],
        ),
    ],
)
def test_rsync_publisher(target_url, called_command, tmpdir, mocker, env):
    publisher = RsyncPublisher(env, str(output_path))
    target_url = url_parse(target_url)
    ssh_path = join(output_path, "ssh")
    mock_popen = mocker.patch("lektor.publisher.portable_popen")
    publisher.get_command(target_url, str(ssh_path), credentials=None)
    assert mock_popen.called
    assert mock_popen.call_args[0] == (called_command,)
