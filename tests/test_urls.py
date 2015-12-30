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
