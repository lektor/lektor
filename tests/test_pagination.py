def test_paginated_children(pad):
    page1 = pad.get('/projects', page_num=1)

    assert page1 is not None
    assert page1['_model'] == 'projects'
    assert page1['_template'] == 'projects.html'

    assert page1.datamodel.pagination_config.per_page == 4

    assert page1.children.count() == 8
    assert page1.page_num == 1
    assert page1.pagination.items.count() == 4

    children = page1.pagination.items.all()
    assert len(children) == 4
    assert [x['name'] for x in children] == [
        u'Coffee',
        u'Bagpipe',
        u'Master',
        u'Oven',
    ]

    assert ('projects', '_primary', '1') in pad.cache.persistent
    assert ('projects', '_primary', '2') not in pad.cache.persistent

    page2 = pad.get('/projects', page_num=2)

    assert page2.children.count() == 8
    assert page2.page_num == 2
    assert page2.pagination.items.count() == 3

    children = page2.pagination.items.all()
    assert len(children) == 3
    assert [x['name'] for x in children] == [
        u'Postage',
        u'Slave',
        u'Wolf',
    ]

    assert ('projects', '_primary', '2') in pad.cache.persistent


def test_unpaginated_children(pad):
    page_all = pad.get('/projects')

    assert page_all

    assert page_all.pagination.items.count() == 7
    assert page_all.page_num is None

    children = page_all.pagination.items.all()
    assert len(children) == 7
    assert [x['name'] for x in children] == [
        u'Coffee',
        u'Bagpipe',
        u'Master',
        u'Oven',
        u'Postage',
        u'Slave',
        u'Wolf',
    ]


def test_pagination_access(pad):
    page = pad.get('/projects', page_num=1)

    assert page.pagination.page == 1
    assert page.pagination.next.pagination.page == 2
    assert page.pagination.for_page(2).pagination.page == 2

    assert page.pagination.for_page(0) is None
    assert page.pagination.for_page(3) is None

    assert pad.get('/projects@1').page_num == 1
    assert pad.get('/projects@2').page_num == 2
    assert pad.get('/projects@3').page_num == 3


def test_pagination_attributes(pad):
    page = pad.get('/projects', page_num=1)
    assert page.pagination.current is page
    assert page.pagination.next is not None
    assert page.pagination.next.page_num == 2
    assert page.pagination.prev is None
    assert page.pagination.pages == 2
    assert page.pagination.prev_num is None
    assert page.pagination.next_num == 2
    assert page.pagination.has_next
    assert not page.pagination.has_prev

    page = page.pagination.next
    assert page.pagination.current is page
    assert page.pagination.next is None
    assert page.pagination.prev.page_num == 1
    assert not page.pagination.has_next
    assert page.pagination.next is None
    assert page.pagination.next_num is None


def test_url_matching_for_pagination(pad):
    page1 = pad.resolve_url_path('/projects/')
    assert page1.page_num == 1

    page2 = pad.resolve_url_path('/projects/page/2/')
    assert page2.page_num == 2

    page1_explicit = pad.resolve_url_path('/projects/page/1/')
    assert page1_explicit is None


def test_parent_access(pad):
    page2 = pad.resolve_url_path('/projects/page/2/')
    assert page2['_path'] == '/projects'
    assert page2.path == '/projects@2'
    assert page2.page_num == 2

    child = page2.pagination.items.first()
    assert child.parent.path == page2['_path']
    assert child.parent.page_num is None


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
        u'Kaffee',
        u'Dudelsack',
        u'Meister',
        u'Ofen',
        u'Porto',
        u'Sklave',
        u'Wolf',
        u'Zaun'
    ]


def test_prev_next(pad):
    # coffee, bagpipe, filtered, master have seq numbers 9, 8, 7, 6.
    # They disagree with alphabetization, to ensure we use the pagination
    # query order, "-seq".
    bagpipe = pad.get('/projects/bagpipe')
    assert bagpipe.get_siblings().prev_page['_id'] == 'coffee'

    # Next child "filtered" is skipped by pagination query, skip to "master".
    assert bagpipe.get_siblings().next_page['_id'] == 'master'

    # Postage is on the previous page before oven, but prev / next ignore pages.
    oven = pad.get('/projects/oven')
    assert oven.get_siblings().prev_page['_id'] == 'master'
    assert oven.get_siblings().next_page['_id'] == 'postage'


def test_url_matching_for_alt_pagination(pad):
    page1 = pad.resolve_url_path('/de/projects/')
    assert page1.alt == 'de'
    assert page1.page_num == 1

    page2 = pad.resolve_url_path('/de//projects/page/2/')
    assert page2.alt == 'de'
    assert page2.page_num == 2

    page1_explicit = pad.resolve_url_path('/de/projects/page/1/')
    assert page1_explicit is None


def test_pagination_items_filter(pad):
    # This tests that items are excluded from the pagination based on a
    # query if needed.
    blog = pad.get('/blog', page_num=1)
    assert blog.datamodel.pagination_config.items == \
        "this.children.filter(F._model == 'blog-post')"

    assert blog.children.count() == 3
    assert sorted(x['_id'] for x in blog.children) == [
        'dummy.xml', 'post1', 'post2']

    assert blog.pagination.items.count() == 2
    # Sort order is pub_date descending, so post 2 is first.
    assert blog.pagination.items.first()['_id'] == 'post2'

    dummy = blog.children.get('dummy.xml')
    assert dummy is not None
    assert dummy['_model'] == 'none'


def test_virtual_path_behavior(pad):
    # Base record
    blog = pad.get('/blog')
    assert blog.path == '/blog'
    assert blog['_path'] == '/blog'
    assert blog.page_num is None
    assert blog.url_path == '/blog/'
    assert blog.record is blog

    # Record for page 1 which is a bit special
    blog_page1 = pad.get('/blog@1')
    assert blog_page1.path == '/blog@1'
    assert blog_page1['_path'] == '/blog'
    assert blog_page1.url_path == '/blog/'
    assert blog_page1.page_num == 1
    assert blog_page1.parent is pad.root
    assert blog_page1.record is blog

    # Record for page 2 which is slightly less special
    blog_page2 = pad.get('/blog@2')
    assert blog_page2.path == '/blog@2'
    assert blog_page2['_path'] == '/blog'
    assert blog_page2.url_path == '/blog/page/2/'
    assert blog_page2.page_num == 2
    assert blog_page2.parent is pad.root
    assert blog_page2.record is blog

    # Make sure URL generation works as you would expect:
    assert blog.url_to('@1', absolute=True) == '/blog/'
    assert blog.url_to('@2', absolute=True) == '/blog/page/2/'
    assert blog.url_to('..', absolute=True) == '/'
    assert blog_page2.url_to('..', absolute=True) == '/'
    assert blog_page2.url_to('@1', absolute=True) == '/blog/'
    assert blog_page2.url_to('@3', absolute=True) == '/blog/page/3/'
