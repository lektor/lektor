def test_root(pad):
    record = pad.root

    assert record is not None
    assert record['title'] == 'Welcome'
    assert record['_template'] == 'page.html'
    assert record['_alt'] == '_primary'
    assert record['_slug'] == ''
    assert record['_id'] == ''
    assert record['_path'] == '/'


def test_project_implied_model(pad):
    project = pad.query('/projects').first()
    assert project is not None
    assert project['_model'] == 'project'


def test_child_query_visibility_setting(pad):
    projects = pad.get('/projects')
    assert not projects.children._include_hidden

    project_query = pad.query('/projects')
    assert project_query._include_hidden
    assert not project_query._include_undiscoverable


def test_alt_fallback(pad):
    # page that is missing a german tranlation
    wolf_page = pad.get('/projects/wolf', alt='de')

    # Falls back to primary
    assert wolf_page.alt == 'de'
    assert wolf_page['_source_alt'] == '_primary'
    assert wolf_page['name'] == 'Wolf'


def test_alt_parent(pad):
    wolf_page = pad.get('/projects/wolf', alt='de')
    assert wolf_page.alt == 'de'
    assert wolf_page.alt == wolf_page.parent.alt


def test_url_matching_with_customized_slug_in_alt(pad):
    en = pad.resolve_url_path('/projects/slave/')
    assert en.alt == 'en'
    assert en['_source_alt'] == '_primary'
    assert en.path == '/projects/slave'

    de = pad.resolve_url_path('/de/projects/sklave/')
    assert de.alt == 'de'
    assert de['_source_alt'] == 'de'
    assert de.path == '/projects/slave'


def test_basic_query_syntax(pad, F):
    projects = pad.get('/projects')

    encumbered = projects.children.filter(
        (F._slug == 'master') |
        (F._slug == 'slave')
    ).order_by('_slug').all()

    assert len(encumbered) == 2
    assert [x['name'] for x in encumbered] == ['Master', 'Slave']


def test_basic_query_syntax_template(pad, eval_expr):
    projects = pad.get('/projects')

    encumbered = eval_expr('''
        this.children.filter(
            (F._slug == 'master').or(F._slug == 'slave')
        ).order_by('_slug')
    ''', pad=pad, this=projects).all()

    assert len(encumbered) == 2
    assert [x['name'] for x in encumbered] == ['Master', 'Slave']


def test_is_child_of(pad):
    projects = pad.get('/projects')
    assert projects.is_child_of(projects)
    assert not projects.is_child_of(projects, strict=True)
    child = projects.children.first()
    assert child.is_child_of(projects)
    assert child.is_child_of(projects, strict=True)


def test_undiscoverable_basics(pad):
    projects = pad.query('/projects')
    assert projects.count() == 7
    assert projects.include_undiscoverable(True).count() == 8
    assert pad.get('/projects').children.count() == 7
    assert 'secret' not in [x['_id'] for x in pad.get('/projects').children]
    assert not projects._include_undiscoverable
    assert projects._include_hidden

    secret = pad.get('/projects/secret')
    assert secret.is_undiscoverable
    assert secret.url_path == '/projects/secret/'

    q = secret.children
    assert q._include_undiscoverable is False
    assert q._include_hidden is None
    q = q.include_undiscoverable(True)
    assert q._include_undiscoverable is True
    assert q._include_hidden is False

    secret = pad.resolve_url_path('/projects/secret')
    assert secret is not None
    assert secret.path == '/projects/secret'


def test_attachment_api(pad):
    from lektor.db import Image

    root = pad.root
    assert root.attachments.count() == 2
    assert sorted(x['_id'] for x in root.attachments) == [
        'hello.txt', 'test.jpg']

    txt = root.attachments.get('hello.txt')
    assert txt is not None
    assert txt['_attachment_type'] == 'text'
    assert txt.url_path == '/hello.txt'

    img = root.attachments.get('test.jpg')
    assert img is not None
    assert img['_attachment_type'] == 'image'
    assert isinstance(img, Image)
    assert img.url_path == '/test.jpg'
