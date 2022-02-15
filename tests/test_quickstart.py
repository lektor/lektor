import os

import pytest

from lektor.quickstart import get_default_author
from lektor.quickstart import get_default_author_email
from lektor.utils import locate_executable


def test_default_author(os_user):
    assert get_default_author() == "Lektor Test"


@pytest.mark.skipif(locate_executable("git") is None, reason="git not installed")
def test_default_author_email():
    assert isinstance(get_default_author_email(), str)


def test_default_author_email_git_unavailable(monkeypatch):
    monkeypatch.setitem(os.environ, "PATH", "/dev/null")
    locate_executable.cache_clear()
    assert get_default_author_email() is None
