from lektor._compat import text_type
from lektor.quickstart import get_default_author
from lektor.quickstart import get_default_author_email


def test_default_author(os_user):
    assert get_default_author() == "Lektor Test"


def test_default_author_email():
    assert isinstance(get_default_author_email(), text_type)
