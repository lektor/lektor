def test_default_author(os_user):
    from lektor.quickstart import get_default_author
    assert get_default_author() == "Lektor Test"


def test_default_author_email(git_user_email):
    from lektor.quickstart import get_default_author_email
    assert get_default_author_email() == "lektortest@example.com"
