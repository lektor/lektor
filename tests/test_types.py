import datetime

from lektor._compat import itervalues, text_type
from lektor.datamodel import Field
from lektor.types.formats import MarkdownDescriptor
from lektor.context import Context
from lektor.types import Undefined, BadValue

from markupsafe import escape, Markup

from babel.dates import get_timezone


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


def test_markdown_links(env, pad):
    field = make_field(env, 'markdown')
    source = DummySource()

    def md(s):
        rv = field.deserialize_value(s, pad=pad)
        assert isinstance(rv, MarkdownDescriptor)
        return text_type(rv.__get__(source)).strip()

    with Context(pad=pad):
        assert md('[foo](http://example.com/)') == (
            '<p><a href="http://example.com/">foo</a></p>'
        )
        assert md('[foo](javascript:foo)') == (
            '<p><a href="javascript:foo">foo</a></p>'
        )

        img = (
            'iVBORw0KGgoAAAANSUhEUgAAAAUAAAAFCAYAAACNbyblAAAAHElEQVQI12P4'
            '//8/w38GIAXDIBKE0DHxgljNBAAO9TXL0Y4OHwAAAABJRU5ErkJggg=='
        )
        assert md('![test](data:image/png;base64,%s)' % img) == (
            '<p><img src="data:image/png;base64,%s" alt="test"></p>'
        ) % img


def test_markdown_linking(pad, builder):
    blog_index = pad.get('/blog', page_num=1)

    prog, _ = builder.build(blog_index)
    with prog.artifacts[0].open('rb') as f:
        assert (
            b'Look at my <a href="../blog/2015/12/post1/hello.txt">'
            b'attachment</a>'
        ) in f.read()

    blog_post = pad.get('/blog/post1')

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
            b'This is an image <img src="../blog/2015/12/'
            b'post1/logo.png" alt="logo">.'
        ) in f.read()

    blog_post = pad.get('/blog/post1')

    prog, _ = builder.build(blog_post)
    with prog.artifacts[0].open('rb') as f:
        assert (
            b'This is an image <img src="../../../../blog/'
            b'2015/12/post1/logo.png" alt="logo">.'
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


def test_datetime(env, pad):
    field = make_field(env, 'datetime')

    with Context(pad=pad):
        # default
        rv = field.deserialize_value('2016-04-30 01:02:03', pad=pad)
        assert isinstance(rv, datetime.datetime)
        assert rv.year == 2016
        assert rv.month == 4
        assert rv.day == 30
        assert rv.hour == 1
        assert rv.minute == 2
        assert rv.second == 3
        assert rv.tzinfo is None

        # It is not datetime, it is None
        rv = field.deserialize_value(None, pad=pad)
        assert isinstance(rv, Undefined)

        # It is not datetime, it is empty string
        rv = field.deserialize_value('', pad=pad)
        assert isinstance(rv, BadValue)

        # It is not datetime, it is date
        rv = field.deserialize_value('2016-04-30', pad=pad)
        assert isinstance(rv, BadValue)

        # Known timezone name, UTC
        rv = field.deserialize_value('2016-04-30 01:02:03 UTC', pad=pad)
        assert isinstance(rv, datetime.datetime)
        assert rv.year == 2016
        assert rv.month == 4
        assert rv.day == 30
        assert rv.hour == 1
        assert rv.minute == 2
        assert rv.second == 3
        assert rv.tzinfo is get_timezone('UTC')

        # Known timezone name, EST
        rv = field.deserialize_value('2016-04-30 01:02:03 EST', pad=pad)
        assert isinstance(rv, datetime.datetime)
        assert rv.year == 2016
        assert rv.month == 4
        assert rv.day == 30
        assert rv.hour == 1
        assert rv.minute == 2
        assert rv.second == 3
        assert rv.tzinfo is get_timezone('EST')

        # Known location name, Asia/Seoul
        rv = field.deserialize_value('2016-04-30 01:02:03 Asia/Seoul', pad=pad)
        assert isinstance(rv, datetime.datetime)
        assert rv.year == 2016
        assert rv.month == 4
        assert rv.day == 30
        assert rv.hour == 1
        assert rv.minute == 2
        assert rv.second == 3
        assert rv.tzinfo in itervalues(get_timezone('Asia/Seoul')._tzinfos)

        # KST - http://www.timeanddate.com/time/zones/kst
        rv = field.deserialize_value('2016-04-30 01:02:03 +0900', pad=pad)
        assert isinstance(rv, datetime.datetime)
        assert rv.year == 2016
        assert rv.month == 4
        assert rv.day == 30
        assert rv.hour == 1
        assert rv.minute == 2
        assert rv.second == 3
        assert rv.tzinfo._offset == datetime.timedelta(0, 9 * 60 * 60)

        # ACST - http://www.timeanddate.com/time/zones/acst
        rv = field.deserialize_value('2016-04-30 01:02:03 +0930', pad=pad)
        assert isinstance(rv, datetime.datetime)
        assert rv.year == 2016
        assert rv.month == 4
        assert rv.day == 30
        assert rv.hour == 1
        assert rv.minute == 2
        assert rv.second == 3
        assert rv.tzinfo._offset == datetime.timedelta(0, (9 * 60 + 30) * 60)

        # MST - http://www.timeanddate.com/time/zones/mst
        rv = field.deserialize_value('2016-04-30 01:02:03 -0700', pad=pad)
        assert isinstance(rv, datetime.datetime)
        assert rv.year == 2016
        assert rv.month == 4
        assert rv.day == 30
        assert rv.hour == 1
        assert rv.minute == 2
        assert rv.second == 3
        assert rv.tzinfo._offset == datetime.timedelta(0, -7 * 60 * 60)

        # MART - http://www.timeanddate.com/time/zones/mart
        rv = field.deserialize_value('2016-04-30 01:02:03 -0930', pad=pad)
        assert isinstance(rv, datetime.datetime)
        assert rv.year == 2016
        assert rv.month == 4
        assert rv.day == 30
        assert rv.hour == 1
        assert rv.minute == 2
        assert rv.second == 3
        assert rv.tzinfo._offset == datetime.timedelta(0, -(9 * 60 + 30) * 60)

        # with timezone name (case 1)
        rv = field.deserialize_value('2016-04-30 01:02:03 KST +0900', pad=pad)
        assert isinstance(rv, datetime.datetime)
        assert rv.year == 2016
        assert rv.month == 4
        assert rv.day == 30
        assert rv.hour == 1
        assert rv.minute == 2
        assert rv.second == 3
        assert rv.tzinfo._offset == datetime.timedelta(0, 9 * 60 * 60)

        # with timezone name (case 2)
        rv = field.deserialize_value('2016-04-30 01:02:03 KST+0900', pad=pad)
        assert isinstance(rv, datetime.datetime)
        assert rv.year == 2016
        assert rv.month == 4
        assert rv.day == 30
        assert rv.hour == 1
        assert rv.minute == 2
        assert rv.second == 3
        assert rv.tzinfo._offset == datetime.timedelta(0, 9 * 60 * 60)
