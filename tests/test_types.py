from lektor.datamodel import Field
from lektor.markdown import Markdown
from lektor.context import Context
from lektor.types import Undefined

from markupsafe import escape, Markup


def make_field(env, type, **options):
    return Field(env, 'demo', type=env.types[type],
                 options=options)


def test_markdown(env, pad):
    field = make_field(env, 'markdown')

    with Context(pad=pad):
        rv = field.deserialize_value('Hello **World**!', pad=pad)
        assert isinstance(rv, Markdown)
        assert rv
        assert rv.source == 'Hello **World**!'
        assert escape(rv) == Markup('<p>Hello <strong>World</strong>!</p>\n')
        assert rv.meta == {}

        for val in '', None:
            rv = field.deserialize_value(val, pad=pad)
            assert isinstance(rv, Markdown)
            assert not rv
            assert rv.source == ''
            assert escape(rv) == Markup('')
            assert rv.meta == {}


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


def test_html(env, pad):
    field = make_field(env, 'html')

    with Context(pad=pad):
        rv = field.deserialize_value('', pad=pad)
        assert isinstance(rv, Markup)
        assert rv == Markup('')

        rv = field.deserialize_value('<em>Foo</em>', pad=pad)
        assert isinstance(rv, Markup)
        assert rv == Markup('<em>Foo</em>')
