import os
from datetime import date

from lektor.context import Context
from lektor.db import get_alts


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

    # If we ask for the alts of that page, we will only get english
    assert get_alts(wolf_page) == ['en']

    # Unless we include fallbacks in which case we will also see german
    # show up in the list.
    assert get_alts(wolf_page, fallback=True) == ['en', 'de']


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

    assert get_alts(en) == ['en', 'de']


def test_basic_alts(pad):
    with Context(pad=pad):
        assert get_alts() == ['en', 'de']


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
    assert projects.count() == 8
    assert projects.include_undiscoverable(True).count() == 9
    assert pad.get('/projects').children.count() == 8
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


def test_query_normalization(pad):
    projects = pad.get('projects')
    assert pad.get('projects') is projects
    assert pad.get('/projects') is projects
    assert pad.get('/projects/.') is projects
    assert pad.get('//projects/.') is projects


def test_distinct(pad):
    posts = pad.query('blog')
    distinct_categories = posts.distinct('category')
    assert isinstance(distinct_categories, set)
    assert distinct_categories == set(['My Category'])
    distinct_tags = posts.distinct('tags')
    assert isinstance(distinct_tags, set)
    assert distinct_tags == set(['tag1', 'tag2', 'tag3'])
    distinct_pub_dates = posts.distinct('pub_date')
    assert distinct_pub_dates == set([date(2015, 12, 12), date(2015, 12, 13)])
    assert posts.distinct('foo') == set()
    # Post 2 has no summary; check we don't include Undefined in distinct().
    assert posts.distinct('summary') == set(['hello'])


def test_root_pagination(scratch_project, scratch_env):
    base = scratch_project.tree
    with open(os.path.join(base, 'models', 'page.ini'), 'w') as f:
        f.write(
            '[model]\n'
            'label = {{ this.title }}\n\n'
            '[children]\n'
            'model = page\n'
            '[pagination]\n'
            'enabled = yes\n'
            'per_page = 1\n'
            '[fields.title]\n'
            'type = string\n'
            '[fields.body]\n'
            'type = markdown\n'
        )

    for name in 'a', 'b', 'c':
        os.mkdir(os.path.join(base, 'content', name))
        with open(os.path.join(base, 'content', name, 'contents.lr'), 'w') as f:
            f.write(
                '_model: page\n'
                '---\n'
                'title: Page %s\n'
                '---\n'
                'body: Hello World!\n' % name
            )

    from lektor.db import Database
    scratch_pad = Database(scratch_env).new_pad()

    root = scratch_pad.root
    assert root.children.count() == 3

    root_1 = scratch_pad.resolve_url_path('/')
    assert root_1.page_num == 1

    root_2 = scratch_pad.resolve_url_path('/page/2/')
    assert root_2.page_num == 2


def test_undefined_order(pad):
    # A missing value should sort after all others.
    blog_post = pad.db.datamodels['blog-post']

    from lektor.db import Query

    class TestQuery(Query):
        def _iterate(self):
            for day, pub_date in [
                (3, '2016-01-03'),
                (4, None),              # No pub_date.
                (1, '2016-01-01'),
                (2, '2016-01-02'),
            ]:
                yield pad.instance_from_data({
                    '_id': str(day),
                    '_path': 'test/%s' % day,
                    'pub_date': pub_date},
                    datamodel=blog_post)

    ids = [c['_id'] for c in TestQuery('test', pad).order_by('pub_date')]
    assert ['4', '1', '2', '3'] == ids

    ids = [c['_id'] for c in TestQuery('test', pad).order_by('-pub_date')]
    assert ['3', '2', '1', '4'] == ids


def test_hidden_flag(pad):
    # This page is just not hidden at all
    post = pad.get('blog/post1')
    assert not post.is_hidden

    # The root is never hidden itself unless forced
    root = pad.get('/')
    assert not root.is_hidden

    # The container is hidden
    container = pad.get('extra/container')
    assert container.is_hidden

    # But the child of the container is not
    a = pad.get('extra/container/a')
    assert not a.is_hidden
    assert container.children.all() == [a]

    # Attachments are also always visible
    attachment = pad.get('extra/container/hello.txt')
    assert not attachment.is_hidden


def test_default_order_by(scratch_project, scratch_env):
    from lektor.db import Database

    tree = scratch_project.tree
    with open(os.path.join(tree, 'models', 'mymodel.ini'), 'w') as f:
        f.write(
            '[children]\n'
            'order_by = title\n'
            '[attachments]\n'
            'order_by = attachment_filename\n'
            )
    os.mkdir(os.path.join(tree, 'content', 'myobj'))
    with open(os.path.join(tree, 'content', 'myobj', 'contents.lr'), 'w') as f:
        f.write(
            '_model: mymodel\n'
            '---\n'
            'title: My Test Object\n'
            )

    pad = Database(scratch_env).new_pad()
    myobj = pad.get('/myobj')
    children = myobj.children
    assert list(children.get_order_by()) == ['title']
    assert list(children.order_by('explicit').get_order_by()) == ['explicit']
    assert list(myobj.attachments.get_order_by()) == ['attachment_filename']
