import os
from typing import NamedTuple

import pytest

from lektor.builder import Builder
from lektor.project import Project
from lektor.quickstart import Generator
from lektor.quickstart import get_default_author
from lektor.quickstart import get_default_author_email
from lektor.utils import locate_executable


@pytest.mark.parametrize("with_blog", [False, True])
@pytest.mark.parametrize(
    ("project_name", "escaped_name"),
    [
        ("Site & friends", "Site &amp; friends"),
        pytest.param(
            'Site <bar> & "friends"',
            "Site &lt;bar&gt; &amp; &#34;friends&#34;",
            marks=pytest.mark.skipif(
                os.name == "nt",
                reason="project name contains invalid filename characters",
            ),
        ),
    ],
)
def test_project_html_escaping(tmp_path, with_blog, project_name, escaped_name):
    """Quickstart names remain literal text in the generated site's HTML."""
    author_name = "Author <baz> & 'friends'"
    project_path = tmp_path / "project"
    Generator("project").run(
        {
            "project_name": project_name,
            "author_name": author_name,
            "with_blog": with_blog,
            "this_year": 2026,
            "today": "2026-01-01",
        },
        project_path,
    )

    project = Project.from_path(project_path)
    assert project is not None
    assert project.name == project_name
    env = project.make_env(load_plugins=False)
    pad = env.new_pad()
    assert pad.get("/")["title"] == f"Welcome to {project_name}!"
    if with_blog:
        assert pad.get("/blog/first-post")["author"] == author_name

    output_path = tmp_path / "output"
    assert Builder(pad, str(output_path)).build_all() == 0
    html = (output_path / "index.html").read_text(encoding="utf-8")
    assert f" — {escaped_name}</title>" in html
    assert f"<h1>{escaped_name}</h1>" in html
    assert "by Author &lt;baz&gt; &amp; &#39;friends&#39;." in html


class struct_passwd(NamedTuple):
    pw_name: str = "user"
    pw_passwd: str = "pw"
    pw_uid: int = 10000
    pw_gid: int = 10000
    pw_gecos: str = "gecos"
    pw_dir: str = "/tmp"
    pw_shell: str = "/bin/false"


@pytest.fixture
def git_config_file(tmp_path, monkeypatch):
    """Create a temporary git config file, and monkeypatch $GIT_CONFIG to point to
    it."""
    config_file = tmp_path / "git_config"
    config_file.touch()
    monkeypatch.setitem(os.environ, "GIT_CONFIG", str(config_file))
    return config_file


@pytest.mark.skipif(os.name == "nt", reason="windows")
def test_default_author_from_pwd(mocker):
    pw_gecos = "Lektor Tester,,555-1212,,"
    mocker.patch(
        "pwd.getpwuid", spec=True, return_value=struct_passwd(pw_gecos=pw_gecos)
    )
    assert get_default_author() == "Lektor Tester"


def test_default_author_from_username(mocker):
    mocker.patch("getpass.getuser", spec=True, return_value="lektortester")
    if os.name != "nt":
        mocker.patch("os.getuid", spec=True, return_value=-1)
    assert get_default_author() == "lektortester"


@pytest.mark.skipif(locate_executable("git") is None, reason="git not installed")
def test_default_author_email(git_config_file):
    git_config_file.write_text("[user]\n\temail = tester@example.com\n")
    assert get_default_author_email() == "tester@example.com"


@pytest.mark.usefixtures("no_utils")
def test_default_author_email_from_EMAIL(monkeypatch):
    email = "tester@example.net"
    monkeypatch.setitem(os.environ, "EMAIL", email)
    assert get_default_author_email() == email


@pytest.mark.usefixtures("no_utils")
def test_default_author_email_no_default(monkeypatch):
    monkeypatch.delitem(os.environ, "EMAIL", raising=False)
    assert get_default_author_email() is None
