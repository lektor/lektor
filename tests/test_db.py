def test_root(pad):
    record = pad.root

    assert record is not None
    assert record['title'] == 'Welcome'
    assert record['_template'] == 'page.html'
    assert record['_alt'] == '_primary'
    assert record['_slug'] == ''
    assert record['_id'] == ''
    assert record['_path'] == '/'


def test_paginated_children(pad):
    page1 = pad.get('/projects', page_num=1)

    assert page1 is not None
    assert page1['_model'] == 'projects'
    assert page1['_template'] == 'projects.html'

    assert page1.datamodel.pagination_config.per_page == 4

    assert page1.children.count() == 7
    assert page1.page_num == 1
    assert page1.pagination.items.count() == 4

    children = page1.pagination.items.all()
    assert len(children) == 4
    assert [x['name'] for x in children] == [
        u'Bagpipe',
        u'Coffee',
        u'Master',
        u'Oven',
    ]

    assert ('projects', '_primary', 1) in pad.cache.persistent
    assert ('projects', '_primary', 2) not in pad.cache.persistent

    page2 = pad.get('/projects', page_num=2)

    assert page2.children.count() == 7
    assert page2.page_num == 2
    assert page2.pagination.items.count() == 3

    children = page2.pagination.items.all()
    assert len(children) == 3
    assert [x['name'] for x in children] == [
        u'Postage',
        u'Slave',
        u'Wolf',
    ]

    assert ('projects', '_primary', 2) in pad.cache.persistent


def test_unpaginated_children(pad):
    page_all = pad.get('/projects')

    assert page_all.pagination.items.count() == 7
    assert page_all.page_num is None

    children = page_all.pagination.items.all()
    assert len(children) == 7
    assert [x['name'] for x in children] == [
        u'Bagpipe',
        u'Coffee',
        u'Master',
        u'Oven',
        u'Postage',
        u'Slave',
        u'Wolf',
    ]


def test_url_matching_for_pagination(pad):
    page1 = pad.resolve_url_path('/projects/')
    assert page1.page_num == 1

    page2 = pad.resolve_url_path('/projects/page/2/')
    assert page2.page_num == 2

    page1_explicit = pad.resolve_url_path('/projects/page/1/')
    assert page1_explicit is None


def test_project_implied_model(pad):
    project = pad.query('/projects').first()
    assert project is not None
    assert project['_model'] == 'project'


def test_child_query_visibility_setting(pad):
    projects = pad.get('/projects')
    assert not projects.children._include_hidden

    project_query = pad.query('/projects')
    assert project_query._include_hidden


def test_pagination_url_paths(pad):
    # Even though this is paginated, getting to the non paginated version
    # just looks like going to the first page.  We do this because it
    # is more convenient for usage.
    project = pad.get('/projects')
    assert project.url_path == '/projects/'

    # However first page looks the same
    project = pad.get('/projects', page_num=1)
    assert project.url_path == '/projects/'

    # second page is different
    project = pad.get('/projects', page_num=2)
    assert project.url_path == '/projects/page/2/'


def test_unpaginated_children_other_alt(pad):
    page_all = pad.get('/projects', alt='de')

    assert page_all.pagination.items.count() == 8
    assert page_all.page_num is None

    children = page_all.pagination.items.all()
    assert len(children) == 8
    assert [x['name'] for x in children] == [
        u'Dudelsack',
        u'Kaffee',
        u'Meister',
        u'Ofen',
        u'Porto',
        u'Sklave',
        u'Wolf',
        u'Zaun'
    ]


def test_alt_fallback(pad):
    # page that is missing a german tranlation
    wolf_page = pad.get('/projects/wolf', alt='de')

    # Falls back to primary
    assert wolf_page.alt == 'de'
    assert wolf_page['_source_alt'] == '_primary'
    assert wolf_page['name'] == 'Wolf'


def test_url_matching_for_alt_pagination(pad):
    page1 = pad.resolve_url_path('/de/projects/')
    assert page1.alt == 'de'
    assert page1.page_num == 1

    page2 = pad.resolve_url_path('/de//projects/page/2/')
    assert page2.alt == 'de'
    assert page2.page_num == 2

    page1_explicit = pad.resolve_url_path('/de/projects/page/1/')
    assert page1_explicit is None


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
