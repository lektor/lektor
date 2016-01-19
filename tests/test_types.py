from lektor.datamodel import Field
from lektor.types.formats import MarkdownDescriptor
from lektor.context import Context
from lektor.types import Undefined, BadValue

from markupsafe import escape, Markup


class DummySource(object):
    url_path = '/'


def make_field(env, type, **options):
    return Field(env, 'demo', type=env.types[type],
                 options=options)


def test_markdown(env, pad):
    field = make_field(env, 'markdown')

    source = DummySource()

    with Context(pad=pad):
        rv = field.deserialize_value('Hello **World**!', pad=pad)
        assert isinstance(rv, MarkdownDescriptor)
        rv = rv.__get__(source)
        assert rv
        assert rv.source == 'Hello **World**!'
        assert escape(rv) == Markup('<p>Hello <strong>World</strong>!</p>\n')
        assert rv.meta == {}

        for val in '', None:
            rv = field.deserialize_value(val, pad=pad)
            assert isinstance(rv, MarkdownDescriptor)
            rv = rv.__get__(source)
            assert not rv
            assert rv.source == ''
            assert escape(rv) == Markup('')
            assert rv.meta == {}


def test_markdown_linking(pad, builder):
    blog_index = pad.get('/blog', page_num=1)

    prog, _ = builder.build(blog_index)
    with prog.artifacts[0].open('rb') as f:
        assert (
            b'Look at my <a href="../blog/2015/12/post1/hello.txt">'
            b'attachment</a>'
        ) in f.read()

    blog_post = pad.get('/blog/post1')
    print blog_post

    prog, _ = builder.build(blog_post)
    with prog.artifacts[0].open('rb') as f:
        assert (
            b'Look at my <a href="../../../../blog/2015/12/post1/hello.txt">'
            b'attachment</a>'
        ) in f.read()

def test_markdown_images(pad, builder):
    blog_index = pad.get('/blog', page_num=1)

    prog, _ = builder.build(blog_index)
    with prog.artifacts[0].open('rb') as f:
        assert (
            b'This is an image <img src="../blog/2015/12/post1/logo.png" alt="logo">.'
        ) in f.read()

    blog_post = pad.get('/blog/post1')

    prog, _ = builder.build(blog_post)
    with prog.artifacts[0].open('rb') as f:
        assert (
            b'This is an image <img src="../../../../blog/2015/12/post1/logo.png" alt="logo">.'
        ) in f.read()

def test_string(env, pad):
    field = make_field(env, 'string')

    with Context(pad=pad):
        rv = field.deserialize_value('', pad=pad)
        assert rv == ''

        rv = field.deserialize_value(None, pad=pad)
        assert isinstance(rv, Undefined)

        rv = field.deserialize_value('foo\nbar', pad=pad)
        assert rv == 'foo'

        rv = field.deserialize_value(' 123 ', pad=pad)
        assert rv == '123'


def test_text(env, pad):
    field = make_field(env, 'text')

    with Context(pad=pad):
        rv = field.deserialize_value('', pad=pad)
        assert rv == ''

        rv = field.deserialize_value(None, pad=pad)
        assert isinstance(rv, Undefined)

        rv = field.deserialize_value('foo\nbar', pad=pad)
        assert rv == 'foo\nbar'

        rv = field.deserialize_value(' 123 ', pad=pad)
        assert rv == ' 123 '


def test_integer(env, pad):
    field = make_field(env, 'integer')

    with Context(pad=pad):
        rv = field.deserialize_value('', pad=pad)
        assert isinstance(rv, BadValue)

        rv = field.deserialize_value(None, pad=pad)
        assert isinstance(rv, Undefined)

        rv = field.deserialize_value('42', pad=pad)
        assert rv == 42

        rv = field.deserialize_value(' 23 ', pad=pad)
        assert rv == 23


def test_float(env, pad):
    field = make_field(env, 'float')

    with Context(pad=pad):
        rv = field.deserialize_value('', pad=pad)
        assert isinstance(rv, BadValue)

        rv = field.deserialize_value(None, pad=pad)
        assert isinstance(rv, Undefined)

        rv = field.deserialize_value('42', pad=pad)
        assert rv == 42.0

        rv = field.deserialize_value(' 23.0 ', pad=pad)
        assert rv == 23.0

        rv = field.deserialize_value('-23.5', pad=pad)
        assert rv == -23.5


def test_boolean(env, pad):
    field = make_field(env, 'boolean')

    with Context(pad=pad):
        rv = field.deserialize_value('', pad=pad)
        assert isinstance(rv, BadValue)

        rv = field.deserialize_value(None, pad=pad)
        assert isinstance(rv, Undefined)

        for s in 'true', 'TRUE', 'True', '1', 'yes':
            rv = field.deserialize_value(s, pad=pad)
            assert rv is True

        for s in 'false', 'FALSE', 'False', '0', 'no':
            rv = field.deserialize_value(s, pad=pad)
            assert rv is False
