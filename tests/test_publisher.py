import pytest
from lektor.publisher import GithubPagesPublisher, PublishError

@pytest.mark.parametrize(
    "test_lines_raises",
    [
        'fatal:',
        'Fatal:',
        'Error:',
        'error:',
        'fatal: couldn\'t find remote ref refs/heads/gh-pages',
        'Fatal: couldn\'t find remote ref refs/heads/gh-pages',
        'error: Could not fetch origin',
        'Error: Could not fetch origin',
        'error: src refspec gh-pages does not match any',
        'Error: src refspec gh-pages does not match any'
    ],
)
def test_github_pages_publisher_check_error_raises(test_lines_raises):
    with pytest.raises(PublishError):
        GithubPagesPublisher._check_error(test_lines_raises)

def test_github_pages_publisher_check_error_passes():
    test_lines_raises = [
        'Initial commit',
        'nothing to commit',
        'On branch gh-pages'
    ]
    for test_line in test_lines_raises:
        print(test_line)
        GithubPagesPublisher._check_error(test_line)
