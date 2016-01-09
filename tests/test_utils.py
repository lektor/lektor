def test_join_path():
    from lektor.utils import join_path

    assert join_path('a', 'b') == 'a/b'
    assert join_path('/a', 'b') == '/a/b'
    assert join_path('a@b', 'c') == 'a@b/c'
    assert join_path('a@b', '') == 'a@b'
    assert join_path('a@b', '@c') == 'a@c'
    assert join_path('a@b/c', 'a@b') == 'a/a@b'

    assert join_path('blog@archive', '2015') == 'blog@archive/2015'
    assert join_path('blog@archive/2015', '..') == 'blog@archive'
    assert join_path('blog@archive/2015', '@archive') == 'blog@archive'
    assert join_path('blog@archive', '..') == 'blog'
    assert join_path('blog@archive', '.') == 'blog@archive'
    assert join_path('blog@archive', '') == 'blog@archive'

    # special behavior: parent of pagination paths is always the actual
    # page parent.
    assert join_path('/blog@1', '..') == '/'
    assert join_path('/blog@2', '..') == '/'

    # But joins on the same level keep the path
    assert join_path('/blog@1', '.') == '/blog@1'
    assert join_path('/blog@2', '.') == '/blog@2'
    assert join_path('/blog@1', '') == '/blog@1'
    assert join_path('/blog@2', '') == '/blog@2'


def test_is_path_child_of():
    from lektor.utils import is_path_child_of

    assert not is_path_child_of('a/b', 'a/b')
    assert is_path_child_of('a/b', 'a/b', strict=False)
    assert is_path_child_of('a/b/c', 'a')
    assert not is_path_child_of('a/b/c', 'b')
    assert is_path_child_of('a/b@foo/bar', 'a/b@foo')
    assert is_path_child_of('a/b@foo', 'a/b@foo', strict=False)
    assert not is_path_child_of('a/b@foo/bar', 'a/c@foo')
    assert not is_path_child_of('a/b@foo/bar', 'a/c')
    assert is_path_child_of('a/b@foo', 'a/b')
    assert is_path_child_of('a/b@foo/bar', 'a/b@foo')
    assert not is_path_child_of('a/b@foo/bar', 'a/b@bar')


def test_url_builder():
    from lektor.utils import build_url

    assert build_url([]) == '/'
    assert build_url(['a', 'b/c']) == '/a/b/c/'
    assert build_url(['a', 'b/c'], trailing_slash=False) == '/a/b/c'
    assert build_url(['a', 'b/c.html']) == '/a/b/c.html'
    assert build_url(['a', 'b/c.html'], trailing_slash=True) == '/a/b/c.html/'
    assert build_url(['a', None, 'b', '', 'c']) == '/a/b/c/'


def test_parse_path():
    from lektor.utils import parse_path
    assert parse_path('') == []
    assert parse_path('/') == []
    assert parse_path('/foo') == ['foo']
    assert parse_path('/foo/') == ['foo']
    assert parse_path('/foo/bar') == ['foo', 'bar']
    assert parse_path('/foo/bar/') == ['foo', 'bar']
    assert parse_path('/foo/bar/../stuff') == ['foo', 'bar', 'stuff']
