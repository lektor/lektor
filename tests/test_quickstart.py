import os
from typing import NamedTuple

import pytest

from lektor.quickstart import get_default_author
from lektor.quickstart import get_default_author_email
from lektor.utils import locate_executable


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
    """Create a temporary git config file, and monkeypatch $GIT_CONFIG to point to it."""
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
