import textwrap
from lektor.publisher import GithubPagesPublisher, RsyncPublisher
from werkzeug.urls import url_parse

def test_get_server(env):
    server = env.load_config().get_server('production')
    assert server.name == 'Production'
    assert server.name_i18n['de'] == 'Produktion'
    assert server.target == 'rsync://myserver.com/path/to/website'
    assert server.extra == {'extra_field': 'extra_value'}


def test_ghpages_update_git_config(tmpdir, env):
    output_path = tmpdir.mkdir("output")
    publisher = GithubPagesPublisher(env, str(output_path))
    repo_path = tmpdir.mkdir("repo")
    repo_config = repo_path.mkdir(".git").join("config").ensure(file=True)
    target_url = url_parse("ghpages://user/repo")
    branch = "master"
    publisher.update_git_config(str(repo_path), target_url, branch)
    expected = textwrap.dedent("""
        [remote "origin"]
        url = git@github.com:user/repo.git
        fetch = +refs/heads/master:refs/remotes/origin/master
    """).strip()
    assert repo_config.read().strip() == expected


def test_ghpages_update_git_config_https(tmpdir, env):
    output_path = tmpdir.mkdir("output")
    publisher = GithubPagesPublisher(env, str(output_path))
    repo_path = tmpdir.mkdir("repo")
    repo_config = repo_path.mkdir(".git").join("config").ensure(file=True)
    target_url = url_parse("ghpages+https://pybee/pybee.github.io?cname=pybee.org")
    branch = "lektor"
    publisher.update_git_config(str(repo_path), target_url, branch)
    expected = textwrap.dedent("""
        [remote "origin"]
        url = https://github.com/pybee/pybee.github.io.git
        fetch = +refs/heads/lektor:refs/remotes/origin/lektor
    """).strip()
    assert repo_config.read().strip() == expected


def test_ghpages_write_cname(tmpdir, env):
    output_path = tmpdir.mkdir("output")
    publisher = GithubPagesPublisher(env, str(output_path))
    target_url = url_parse("ghpages+https://pybee/pybee.github.io?cname=pybee.org")
    publisher.write_cname(str(output_path), target_url)
    assert (output_path / 'CNAME').read() == "pybee.org\n"


def test_rsync_command(tmpdir, mocker, env):
    output_path = tmpdir.mkdir("output")
    publisher = RsyncPublisher(env, str(output_path))
    target_url = url_parse("http://example.com")
    ssh_path = tmpdir.mkdir("ssh")
    mock_popen = mocker.patch("lektor.publisher.portable_popen")
    command = publisher.get_command(target_url, str(ssh_path), credentials=None)
    assert mock_popen.called
    assert mock_popen.call_args[0] == ([
        'rsync', '-rclzv', '--exclude=.lektor',
        str(output_path) + '/',
        'example.com:/'
    ],)


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
    command = publisher.get_command(target_url, str(ssh_path), credentials)
    assert mock_popen.called
    assert mock_popen.call_args[0] == ([
        'rsync', '-rclzv', '--exclude=.lektor',
        str(output_path) + '/',
        'fakeuser@example.com:/'
    ],)


def test_rsync_command_username_in_url(tmpdir, mocker, env):
    output_path = tmpdir.mkdir("output")
    publisher = RsyncPublisher(env, str(output_path))
    target_url = url_parse("http://fakeuser@example.com")
    ssh_path = tmpdir.mkdir("ssh")
    mock_popen = mocker.patch("lektor.publisher.portable_popen")
    command = publisher.get_command(target_url, str(ssh_path), credentials=None)
    assert mock_popen.called
    assert mock_popen.call_args[0] == ([
        'rsync', '-rclzv', '--exclude=.lektor',
        str(output_path) + '/',
        'fakeuser@example.com:/'
    ],)
