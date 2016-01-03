def test_basic_editor(scratch_tree):
    sess = scratch_tree.edit('/')

    assert sess.id == ''
    assert sess.path == '/'
    assert sess.record is not None

    assert sess['_model'] == 'page'
    assert sess['title'] == 'Index'
    assert sess['body'] == 'Hello World!'

    sess['body'] = 'A new body'
    sess.commit()

    assert sess.closed

    with open(sess.get_fs_path()) as f:
        assert f.read().splitlines() == [
            '_model: page',
            '---',
            'title: Index',
            '---',
            'body: A new body'
        ]


def test_create_alt(scratch_tree, scratch_pad):
    sess = scratch_tree.edit('/', alt='de')

    assert sess.id == ''
    assert sess.path == '/'
    assert sess.record is not None

    assert sess['_model'] == 'page'
    assert sess['title'] == 'Index'
    assert sess['body'] == 'Hello World!'

    sess['body'] = 'Hallo Welt!'
    sess.commit()

    assert sess.closed

    # When we use the editor to change this, we only want the fields that
    # changed compared to the base to be included.
    with open(sess.get_fs_path(alt='de')) as f:
        assert f.read().splitlines() == [
            'body: Hallo Welt!'
        ]

    scratch_pad.cache.flush()
    item = scratch_pad.get('/', alt='de')
    assert item['_slug'] == ''
    assert item['title'] == 'Index'
    assert item['body'].source == 'Hallo Welt!'
    assert item['_model'] == 'page'
