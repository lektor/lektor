# -*- coding: utf-8 -*-

from __future__ import unicode_literals


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
        'Bagpipe',
        'Coffee',
        'Master',
        'Oven',
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
        'Postage',
        'Slave',
        'Wolf',
    ]

    assert ('projects', '_primary', 2) in pad.cache.persistent


def test_unpaginated_children(pad):
    page_all = pad.get('/projects')

    assert page_all

    assert page_all.pagination.items.count() == 7
    assert page_all.page_num is None

    children = page_all.pagination.items.all()
    assert len(children) == 7
    assert [x['name'] for x in children] == [
        'Bagpipe',
        'Coffee',
        'Master',
        'Oven',
        'Postage',
        'Slave',
        'Wolf',
    ]


def test_pagination_access(pad):
    page = pad.get('/projects', page_num=1)

    assert page.pagination.page == 1
    assert page.pagination.next.pagination.page == 2
    assert page.pagination.for_page(2).pagination.page == 2

    assert page.pagination.for_page(0) is None
    assert page.pagination.for_page(3) is None


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
        'Dudelsack',
        'Kaffee',
        'Meister',
        'Ofen',
        'Porto',
        'Sklave',
        'Wolf',
        'Zaun'
    ]


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

    assert blog.children.count() == 2
    assert sorted(x['_id'] for x in blog.children) == [
        'dummy.xml', 'post1']

    assert blog.pagination.items.count() == 1
    assert blog.pagination.items.first()['_id'] == 'post1'

    dummy = blog.children.get('dummy.xml')
    assert dummy is not None
    assert dummy['_model'] == 'none'
