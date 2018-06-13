import pytest

def test_cleanup_path():
    from lektor.utils import cleanup_path

    assert cleanup_path('/') == '/'
    assert cleanup_path('/foo') == '/foo'
    assert cleanup_path('/foo/') == '/foo'
    assert cleanup_path('/////foo/') == '/foo'
    assert cleanup_path('/////foo////') == '/foo'
    assert cleanup_path('/////foo/.///') == '/foo'
    assert cleanup_path('/////foo/..///') == '/foo'
    assert cleanup_path('/foo/./bar/') == '/foo/bar'
    assert cleanup_path('/foo/../bar/') == '/foo/bar'


def test_basic_url_to_with_alts(pad):

    wolf_en = pad.get('/projects/wolf', alt='en')
    slave_en = pad.get('/projects/slave', alt='en')
    wolf_de = pad.get('/projects/wolf', alt='de')
    slave_de = pad.get('/projects/slave', alt='de')

    assert wolf_en.url_to(slave_en) == '../../projects/slave/'
    assert wolf_de.url_to(slave_de) == '../../../de/projects/sklave/'
    assert slave_en.url_to(slave_de) == '../../de/projects/sklave/'
    assert slave_de.url_to(slave_en) == '../../../projects/slave/'


@pytest.mark.parametrize("alt, absolute, external, base_url, expected", [
    ("de", None, None, None, '../../de/projects/sklave/'),
    ("de", True, None, None, '/de/projects/sklave/'),
    ("de", True, True, None, '/de/projects/sklave/'), #
    ("de", True, True, '/content/', '/de/projects/sklave/'),#
    ("de", None, True, None, '/projects/slave1/de/projects/sklave/'),
    ("de", None, True, '/content/', '/projects/slave1/de/projects/sklave/'),#
    ("de", None, None, '/content/', '../de/projects/sklave/'),
    (None, True, None, None, '/projects/slave/'),
    (None, True, True, None, '/projects/slave/'),#
    (None, True, True, '/content/', '/projects/slave/'),
    (None, True, None, '/content/', '/projects/slave/'),
    (None, None, True, None, '/projects/slave1/projects/slave/'),
    (None, None, True, '/content/', '/projects/slave1/projects/slave/'),
    (None, None, None, '/content/', '../projects/slave/'),
])
def test_url_to_all_params(pad, alt, absolute, external, base_url, expected):
    if external:
        pad.db.config.base_url = "/projects/slave1/"

    wolf_en = pad.get('/projects/wolf')

    assert wolf_en.url_to("/projects/slave/", alt, absolute, external, base_url) == expected
