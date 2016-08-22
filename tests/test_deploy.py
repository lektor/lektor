import textwrap
from lektor.publisher import GithubPagesPublisher
from werkzeug.urls import url_parse

def test_get_server(env):
    server = env.load_config().get_server('production')
    assert server.name == 'Production'
    assert server.name_i18n['de'] == 'Produktion'
    assert server.target == 'rsync://example.com/path/to/website'
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
