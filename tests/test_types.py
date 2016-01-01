from lektor.datamodel import Field
from lektor.markdown import Markdown
from lektor.context import Context

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

        rv = field.deserialize_value('', pad=pad)
        assert isinstance(rv, Markdown)
        assert not rv
        assert rv.source == ''
        assert escape(rv) == Markup('')
        assert rv.meta == {}
