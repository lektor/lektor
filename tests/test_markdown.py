import re
from typing import Union

import pytest
from markupsafe import Markup

from lektor.context import Context
from lektor.markdown import _markdown_cache
from lektor.markdown import ImprovedRenderer
from lektor.markdown import Markdown
from lektor.markdown import markdown_to_html
from lektor.pluginsystem import Plugin


def _xfail_966(*args):
    return pytest.param(
        *args,
        marks=pytest.mark.xfail(
            reason="Links are not currently resolved to lektor objects. See #966."
        ),
    )


@pytest.fixture
def record_path():
    return "/extra"


@pytest.fixture
def record_alt():
    return "en"


@pytest.fixture
def record(pad, record_path, record_alt):
    return pad.get(record_path, alt=record_alt)


@pytest.fixture
def base_url(record):
    return None


@pytest.fixture
def context(record, base_url):
    if base_url is None:
        base_url = record.url_path
    with Context(pad=record.pad) as ctx:
        with ctx.changed_base_url(base_url):
            yield ctx


@pytest.fixture
def renderer_context(context, record):
    ImprovedRenderer.record = record
    ImprovedRenderer.meta = {}
    try:
        yield
    finally:
        del ImprovedRenderer.record
        del ImprovedRenderer.meta


def _normalize_html(output: Union[str, Markup]) -> str:
    html = str(output).strip()
    html = html.replace("&copy;", "©")
    html = re.sub(r"(<img [^>]*?)\s*/>", r"\1>", html)
    return html


@pytest.mark.parametrize(
    "link, title, text, expected",
    [
        _xfail_966("a", None, "text", r'<a href="a/">text</a>\Z'),
        ("missing", None, "text", r'<a href="missing">text</a>\Z'),
        ("/", "T", "text", r'<a href="../" title="T">text</a>\Z'),
        ("a&amp;b", None, "x", r'.* href="a&amp;b"'),
        ("/", "<title>", "x", r'.* title="&lt;title&gt;"'),
    ],
)
@pytest.mark.usefixtures("renderer_context")
def test_ImprovedRenderer_link(link, title, text, expected):
    renderer = ImprovedRenderer()
    result = renderer.link(link, title, text)
    assert re.match(expected, result)


@pytest.mark.parametrize(
    "src, title, alt, expected",
    [
        ("/test.jpg", None, "text", r'<img src="../test.jpg" alt="text"\s*/?>\Z'),
        ("/test.jpg", "T", "x", r'.* title="T"'),
        ("&amp;c.gif", None, "x", r'.* src="&amp;c.gif"'),
        ("/test.jpg", "<title>", "x", r'.* title="&lt;title&gt;"'),
        ("/test.jpg", None, "x&y", r'.* alt="x&amp;y"'),
    ],
)
@pytest.mark.usefixtures("renderer_context")
def test_ImprovedRenderer_image(src, title, alt, expected):
    renderer = ImprovedRenderer()
    result = renderer.image(src, title, alt)
    assert re.match(expected, result.rstrip())


@pytest.mark.usefixtures("context")
def test_markdown_to_html(record):
    # pylint: disable=unused-variable
    html, meta = markdown_to_html("goober", record)
    assert _normalize_html(html) == "<p>goober</p>"


def test_markdown_to_html_requires_context(record):
    with pytest.raises(RuntimeError):
        markdown_to_html("goober", record)


class LinkCounterPlugin(Plugin):
    """A test plugin to test the renderer meta system."""

    name = "LinkCounter"

    class RendererMixin:
        def link(self, *args, **kwargs):
            self.meta["nlinks"] += 1
            return super().link(*args, **kwargs)

    def on_markdown_config(self, config, **kwargs):
        config.renderer_mixins.append(self.RendererMixin)

    def on_markdown_meta_init(self, meta, **kwargs):
        # pylint: disable=no-self-use
        meta["nlinks"] = 0


@pytest.fixture
def link_counter_plugin(env):
    env.plugin_controller.instanciate_plugin("link-counter", LinkCounterPlugin)


@pytest.fixture
def fresh_markdown_parser(env):
    """Disable Lektor's thread-local caching of Markdown parser."""
    cached = getattr(_markdown_cache, "md", None)
    if cached is not None:
        del _markdown_cache.md
    try:
        yield
    finally:
        if cached is not None:
            _markdown_cache.md = cached


@pytest.mark.parametrize(
    "source, nlinks",
    [
        ("howdy", 0),
        ("[howdy](http://example.com/)", 1),
    ],
)
@pytest.mark.usefixtures("context", "link_counter_plugin", "fresh_markdown_parser")
def test_markdown_to_html_meta(record, source, nlinks):
    # pylint: disable=unused-variable
    html, meta = markdown_to_html(source, record)
    assert meta["nlinks"] == nlinks


class TestMarkdown:
    # pylint: disable=no-self-use

    @pytest.fixture
    def source(self):
        return "text"

    @pytest.fixture
    def markdown(self, source, record):
        return Markdown(source, record)

    @pytest.mark.parametrize("source, expected", [("x", True), ("", False)])
    def test_bool(self, markdown, source, expected):
        assert bool(markdown) is expected

    @pytest.mark.usefixtures("context", "link_counter_plugin")
    def test_meta(self, markdown):
        assert markdown.meta["nlinks"] == 0

    @pytest.mark.usefixtures("context")
    def test_html(self, markdown):
        assert markdown.html.rstrip() == "<p>text</p>"

    @pytest.mark.usefixtures("context", "link_counter_plugin")
    def test_getitem(self, markdown):
        assert markdown["nlinks"] == 0

    @pytest.mark.usefixtures("context")
    def test_str(self, markdown):
        assert str(markdown).rstrip() == "<p>text</p>"

    @pytest.mark.usefixtures("context")
    def test_markup(self, markdown):
        assert markdown.__html__().rstrip() == "<p>text</p>"


@pytest.mark.parametrize(
    "source, expected",
    [
        ("text", r"<p>text</p>\Z"),
        ("&copy;", r"<p>©</p>\Z"),
        # Various link texts
        ("[text](x)", r".*<a [^>]*>text</a>"),
        ("[&copy;](x)", r".*<a [^>]*>©</a>"),
        ("[a&b](x)", r".*<a [^>]*>a&amp;b</a>"),
        ("[a&amp;b](x)", r".*<a [^>]*>a&amp;b</a>"),
        ("[a<>b](x)", r".*<a [^>]*>a&lt;&gt;b</a>"),
        ("[a<br>b](x)", r".*<a [^>]*>a<br>b</a>"),
        # Various link titles
        ('[x](x "TITLE")', r'.*<a\b.* title="TITLE">'),
        ('[x](x "©")', r'.*<a\b.* title="©">'),
        ('[x](x "&copy;")', r'.*<a\b.* title="©">'),
        ('[x](x "a&b")', r'.*<a\b.* title="a&amp;b">'),
        ('[x](x "a&amp;b")', r'.*<a\b.* title="a&amp;b">'),
        ('[x](x "a<br>b")', r'.*<a\b.* title="a&lt;br&gt;b">'),
        # Various link hrefs
        ("[x](&amp;c.html)", r'.*<a\b.* href="&amp;c.html">'),
        ("[x](&c.html)", r'.*<a\b.* href="&amp;c.html">'),
        # Various image alts
        ("![©](x)", r'.*<img\b[^>]* alt="©"'),
        ("![&copy;](x)", r'.*<img\b[^>]* alt="©"'),
        ("![<br>](x)", r'.*<img\b[^>]* alt="&lt;br&gt;"'),
        ("![&](x)", r'.*<img\b[^>]* alt="&amp;"'),
        ("![&amp;](x)", r'.*<img\b[^>]* alt="&amp;"'),
        # Various image titles
        ('![x](y "<br>")', r'.*<img\b[^>]* title="&lt;br&gt;"'),
        ('![x](y "&lt;")', r'.*<img\b[^>]* title="&lt;"'),
        # Various image srcs
        ("![](x&y.gif)", r'.*<img\b[^>]* src="x&amp;y.gif"'),
        ("![](x&amp;y.gif)", r'.*<img\b[^>]* src="x&amp;y.gif"'),
        ("![](x<br>y.gif)", r'.*<img\b[^>]* src="x&lt;br&gt;y.gif"'),
    ],
)
@pytest.mark.usefixtures("context")
def test_integration(record, source, expected):
    rendered = _normalize_html(Markdown(source, record))
    assert re.match(expected, rendered)
