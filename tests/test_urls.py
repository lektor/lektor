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


@pytest.mark.parametrize("path, alt, absolute, external, base_url, expected", [
    ("/projects/slave/", "de", None, None, None, '../../de/projects/sklave/'),
    ("/projects/slave/", "de", True, None, None, '/de/projects/sklave/'),
    ("/projects/slave/", "de", True, True, None, '/de/projects/sklave/'), #
    ("/projects/slave/", "de", True, True, '/content/', '/de/projects/sklave/'),#
    ("/projects/slave/", "de", None, True, None, '/projects/slave1/de/projects/sklave/'),
    ("/projects/slave/", "de", None, True, '/content/', '/projects/slave1/de/projects/sklave/'),#
    ("/projects/slave/", "de", None, None, '/content/', '../de/projects/sklave/'),
    ("/projects/slave/", None, True, None, None, '/projects/slave/'),
    ("/projects/slave/", None, True, True, None, '/projects/slave/'),#
    ("/projects/slave/", None, True, True, '/content/', '/projects/slave/'),
    ("/projects/slave/", None, True, None, '/content/', '/projects/slave/'),
    ("/projects/slave/", None, None, True, None, '/projects/slave1/projects/slave/'),
    ("/projects/slave/", None, None, True, '/content/', '/projects/slave1/projects/slave/'),
    ("/projects/slave/", None, None, None, '/content/', '../projects/slave/'),
])
def test_param(pad, path, alt, absolute, external, base_url, expected):
    if external:
        pad.db.config.base_url = "/projects/slave1/"

    wolf_en = pad.get('/projects/wolf')

    assert wolf_en.url_to(path, alt, absolute, external, base_url) == expected
