import datetime
import re
import warnings

import pytest
from markupsafe import escape
from markupsafe import Markup

from lektor.context import Context
from lektor.datamodel import Field
from lektor.types.base import BadValue
from lektor.types.base import Undefined
from lektor.types.formats import MarkdownDescriptor


class DummySource:
    url_path = "/"

    @staticmethod
    def url_to(url, **kwargs):
        return url


def make_field(env, type, **options):
    return Field(env, "demo", type=env.types[type], options=options)


def test_markdown(env, pad):
    field = make_field(env, "markdown")

    source = DummySource()

    with Context(pad=pad):
        rv = field.deserialize_value("Hello **World**!", pad=pad)
        assert isinstance(rv, MarkdownDescriptor)
        rv = rv.__get__(source)
        assert rv
        assert rv.source == "Hello **World**!"
        assert escape(rv) == Markup("<p>Hello <strong>World</strong>!</p>\n")
        assert rv.meta == {}

        for val in "", None:
            rv = field.deserialize_value(val, pad=pad)
            assert isinstance(rv, MarkdownDescriptor)
            rv = rv.__get__(source)
            assert not rv
            assert rv.source == ""
            assert escape(rv) == Markup("")
            assert rv.meta == {}


def test_markdown_links(env, pad):
    field = make_field(env, "markdown")
    source = DummySource()

    def md(s):
        rv = field.deserialize_value(s, pad=pad)
        assert isinstance(rv, MarkdownDescriptor)
        return str(rv.__get__(source)).strip()

    with Context(pad=pad):
        assert md("[foo](http://example.com/)") == (
            '<p><a href="http://example.com/">foo</a></p>'
        )
        assert md("[foo](javascript:foo)") == (
            '<p><a href="javascript:foo">foo</a></p>'
        )

        img = (
            "iVBORw0KGgoAAAANSUhEUgAAAAUAAAAFCAYAAACNbyblAAAAHElEQVQI12P4"
            "//8/w38GIAXDIBKE0DHxgljNBAAO9TXL0Y4OHwAAAABJRU5ErkJggg=="
        )
        assert re.match(
            rf'<p><img src="data:image/png;base64,{img}" alt="test"\s*/?></p>\Z',
            md(f"![test](data:image/png;base64,{img})"),
        )


def test_markdown_linking(pad, builder):
    blog_index = pad.get("/blog", page_num=1)

    prog, _ = builder.build(blog_index)
    with prog.artifacts[0].open("rb") as f:
        assert (
            b'Look at my <a href="2015/12/post1/hello.txt">' b"attachment</a>"
        ) in f.read()

    blog_post = pad.get("/blog/post1")

    prog, _ = builder.build(blog_post)
    with prog.artifacts[0].open("rb") as f:
        assert b'Look at my <a href="hello.txt">' b"attachment</a>" in f.read()


def test_markdown_images(pad, builder):
    blog_index = pad.get("/blog", page_num=1)

    prog, _ = builder.build(blog_index)
    with prog.artifacts[0].open("rb") as f:
        assert re.search(
            rb'This is an image <img src="2015/12/post1/logo.png" alt="logo"\s*/?>.',
            f.read(),
        )

    blog_post = pad.get("/blog/post1")

    prog, _ = builder.build(blog_post)
    with prog.artifacts[0].open("rb") as f:
        assert re.search(
            rb'This is an image <img src="logo.png" alt="logo"\s*/?>.',
            f.read(),
        )


def test_markdown_warns_on_invalid_options(env):
    with pytest.warns(UserWarning) as warnings:
        make_field(env, "markdown", label="Test", resolve_links="GARBAGE")
    assert "Unrecognized value" in str(warnings[0].message)


@pytest.mark.parametrize("resolve_links", ["always", "never", "when-possible", None])
def test_markdown_does_not_warn_on_valid_options(env, resolve_links):
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        field = make_field(env, "markdown", label="Test", resolve_links=resolve_links)
    assert field.options["resolve_links"] == resolve_links


def test_string(env, pad):
    field = make_field(env, "string")

    with Context(pad=pad):
        rv = field.deserialize_value("", pad=pad)
        assert rv == ""

        rv = field.deserialize_value(None, pad=pad)
        assert isinstance(rv, Undefined)

        rv = field.deserialize_value("foo\nbar", pad=pad)
        assert rv == "foo"

        rv = field.deserialize_value(" 123 ", pad=pad)
        assert rv == "123"


def test_text(env, pad):
    field = make_field(env, "text")

    with Context(pad=pad):
        rv = field.deserialize_value("", pad=pad)
        assert rv == ""

        rv = field.deserialize_value(None, pad=pad)
        assert isinstance(rv, Undefined)

        rv = field.deserialize_value("foo\nbar", pad=pad)
        assert rv == "foo\nbar"

        rv = field.deserialize_value(" 123 ", pad=pad)
        assert rv == " 123 "


def test_integer(env, pad):
    field = make_field(env, "integer")

    with Context(pad=pad):
        rv = field.deserialize_value("", pad=pad)
        assert isinstance(rv, BadValue)

        rv = field.deserialize_value(None, pad=pad)
        assert isinstance(rv, Undefined)

        rv = field.deserialize_value("42", pad=pad)
        assert rv == 42

        rv = field.deserialize_value(" 23 ", pad=pad)
        assert rv == 23


def test_float(env, pad):
    field = make_field(env, "float")

    with Context(pad=pad):
        rv = field.deserialize_value("", pad=pad)
        assert isinstance(rv, BadValue)

        rv = field.deserialize_value(None, pad=pad)
        assert isinstance(rv, Undefined)

        rv = field.deserialize_value("42", pad=pad)
        assert rv == 42.0

        rv = field.deserialize_value(" 23.0 ", pad=pad)
        assert rv == 23.0

        rv = field.deserialize_value("-23.5", pad=pad)
        assert rv == -23.5


def test_boolean(env, pad):
    field = make_field(env, "boolean")

    with Context(pad=pad):
        rv = field.deserialize_value("", pad=pad)
        assert isinstance(rv, BadValue)

        rv = field.deserialize_value(None, pad=pad)
        assert isinstance(rv, Undefined)

        for s in "true", "TRUE", "True", "1", "yes":
            rv = field.deserialize_value(s, pad=pad)
            assert rv is True

        for s in "false", "FALSE", "False", "0", "no":
            rv = field.deserialize_value(s, pad=pad)
            assert rv is False


dt = datetime.datetime


@pytest.mark.parametrize(
    "value, expected",
    [
        ("2016-04-30 01:02:03", dt(2016, 4, 30, 1, 2, 3)),
        ("1970-1-1 12:34", dt(1970, 1, 1, 12, 34)),
        ("1970-01-02 12:34", dt(1970, 1, 2, 12, 34)),
        ("2020-02-03 01:02:03", dt(2020, 2, 3, 1, 2, 3)),
    ],
)
def test_datetime_no_timezone(env, pad, value, expected):
    field = make_field(env, "datetime")
    with Context(pad=pad):
        rv = field.deserialize_value(value, pad=pad)

    assert rv.replace(tzinfo=None) == expected
    assert rv.tzinfo is None


def utc(*args):
    return datetime.datetime(*args, tzinfo=datetime.timezone.utc)


@pytest.mark.parametrize(
    "value, expected",
    [
        # Known timezone name, UTC
        ("2016-04-30 01:02:03 UTC", utc(2016, 4, 30, 1, 2, 3)),
        # Known timezone name, EST
        ("2016-04-30 01:02:03 EST", utc(2016, 4, 30, 6, 2, 3)),
        # Known location name, Asia/Seoul
        ("2016-04-30 01:02:03 Asia/Seoul", utc(2016, 4, 29, 16, 2, 3)),
        # KST - http://www.timeanddate.com/time/zones/kst
        ("2016-04-30 01:02:03 +0900", utc(2016, 4, 29, 16, 2, 3)),
        # ACST - http://www.timeanddate.com/time/zones/acst
        ("2016-04-30 01:02:03 +0930", utc(2016, 4, 29, 15, 32, 3)),
        # MST - http://www.timeanddate.com/time/zones/mst
        ("2016-04-30 01:02:03 -0700", utc(2016, 4, 30, 8, 2, 3)),
        # MART - http://www.timeanddate.com/time/zones/mart
        ("2016-04-30 01:02:03 -0930", utc(2016, 4, 30, 10, 32, 3)),
        # with (ignored) timezone name (case 1)
        ("2016-04-30 01:02:03 KST +0900", utc(2016, 4, 29, 16, 2, 3)),
        # with (ignored) timezone name (case 2)
        ("2016-04-30 01:02:03 KST+0900", utc(2016, 4, 29, 16, 2, 3)),
    ],
)
def test_datetime_timezone(env, pad, value, expected):
    field = make_field(env, "datetime")
    with Context(pad=pad):
        rv = field.deserialize_value(value, pad=pad)
    assert rv.astimezone(expected.tzinfo) == expected


@pytest.mark.parametrize(
    "value",
    [
        "",
        "197",
        "1970",
        "1970-01",
        "1970-01-01",
        "1970-01-01 12",
        "1970-01-01 12.23",
        "1970-01 01:02:03",
        "1970-01-01 12:34 *0800",
        "1970-01-01 12:34 -081",
        "1970-01-01 12:34 a\\b",
        "1970-01-01 12:34 very/unknown/timezone",
        "1970-01-01 12:34 very/long/timezone" + "e" * 1024,
    ],
)
def test_datetime_invalid(env, pad, value):
    field = make_field(env, "datetime")
    with Context(pad=pad):
        rv = field.deserialize_value(value, pad=pad)
    assert isinstance(rv, BadValue)


def test_datetime_missing(env, pad):
    field = make_field(env, "datetime")
    with Context(pad=pad):
        rv = field.deserialize_value(None, pad=pad)
    assert isinstance(rv, Undefined)
    assert "Missing value" in rv._undefined_hint
