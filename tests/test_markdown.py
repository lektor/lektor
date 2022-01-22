import re
import threading
from typing import Union

import pytest
from markupsafe import Markup

from lektor.context import Context
from lektor.markdown import controller_class
from lektor.markdown import get_controller
from lektor.markdown import make_markdown
from lektor.markdown import Markdown
from lektor.markdown import markdown_to_html
from lektor.markdown import MISTUNE_VERSION
from lektor.markdown.controller import get_renderer_context
from lektor.markdown.controller import RendererContext
from lektor.markdown.controller import RendererHelper
from lektor.markdown.controller import require_ctx
from lektor.pluginsystem import Plugin


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
def resolve_links():
    return None


@pytest.fixture
def field_options(resolve_links):
    """Field options"""
    return {
        "label": "Test Markdown Field",
        "type": "markdown",
        "resolve_links": resolve_links,
    }


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
def renderer_context(context, record, field_options):
    with RendererContext(record, {}, field_options) as renderer_context:
        yield renderer_context


def test_require_ctx_raises_if_no_ctx():
    with pytest.raises(RuntimeError) as exc_info:
        require_ctx()
    assert "required for markdown rendering" in str(exc_info.value)


def _run_in_thread(target):
    thread = threading.Thread(target=target)
    thread.start()
    thread.join()


def test_renderer_context_is_thread_local(renderer_context):
    assert get_renderer_context() is renderer_context

    @_run_in_thread
    def assert_no_renderer_context():
        with pytest.raises(RuntimeError):
            get_renderer_context()


@pytest.mark.usefixtures("renderer_context")
def test_RendererHelper_options(field_options):
    helper = RendererHelper()
    assert helper.field_options == field_options


@pytest.mark.parametrize(
    "record_path, record_alt, url, base_url, resolve_links, expected",
    [
        ("/", "en", "test.jpg", None, None, "test.jpg"),
        ("/extra", "en", "missing", "/blog/", None, "../extra/missing"),
        ("/extra", "en", "a", "/blog/", None, "../extra/a/"),
        ("/extra", "en", "slash-slug", None, None, "long/path/"),
        ("/extra", "en", "slash-slug", None, "never", "slash-slug"),
        ("/", "de", "test.jpg", None, None, "../test.jpg"),
    ],
)
@pytest.mark.usefixtures("renderer_context")
def test_RendererHelper_resolve_url(url, expected):
    helper = RendererHelper()
    assert helper.resolve_url(url) == expected


@pytest.mark.parametrize("resolve_links", ["always"])
@pytest.mark.usefixtures("renderer_context")
def test_RendererHelper_resolve_url_raises_when_not_resolvable():
    helper = RendererHelper()
    with pytest.raises(RuntimeError) as exc_info:
        helper.resolve_url("missing")
    assert re.search(r"Can not resolve .*missing", str(exc_info.value))


@pytest.fixture
def markdown_controller(env):
    return controller_class(env)


def test_markdown_controller_parser_caching(markdown_controller):
    parsers = {markdown_controller.parser}

    def get_parser():
        parsers.add(markdown_controller.parser)

    get_parser()
    assert len(parsers) == 1

    _run_in_thread(get_parser)
    if MISTUNE_VERSION.startswith("2."):
        # mistune 2.x's parser is thread-safe. It need not be thread-local.
        assert len(parsers) == 1
    else:
        # mistune 0.x's parser is not thread-safe. We need one for each thread.
        assert len(parsers) == 2


@pytest.mark.parametrize("base_url", ["/BASE/"])
@pytest.mark.usefixtures("context")
def test_markdown_controller_get_cache_key(markdown_controller, base_url):
    assert markdown_controller.get_cache_key() == base_url


def test_markdown_controller_get_cache_key_no_context(markdown_controller):
    assert markdown_controller.get_cache_key() is None


def test_controller_cache(env):
    controller = get_controller(env)
    assert get_controller(env) is controller


@pytest.fixture
def improved_renderer():
    # pylint: disable=import-outside-toplevel
    if MISTUNE_VERSION.startswith("2."):
        from lektor.markdown.mistune2 import ImprovedRenderer
    else:
        from lektor.markdown.mistune0 import ImprovedRenderer
    return ImprovedRenderer()


if MISTUNE_VERSION.startswith("0."):

    @pytest.mark.usefixtures("renderer_context")
    def test_ImprovedRenderer_record(record, improved_renderer):
        with pytest.deprecated_call() as warnings:
            assert improved_renderer.record is record
        assert re.search(
            r"Use .*Renderer\.lektor.record instead", str(warnings[0].message)
        )

    def test_ImprovedRenderer_meta(renderer_context, improved_renderer):
        with pytest.deprecated_call() as warnings:
            assert improved_renderer.meta is renderer_context.meta
        assert re.search(
            r"Use .*Renderer\.lektor.meta instead", str(warnings[0].message)
        )


@pytest.mark.parametrize(
    "link, title, text, expected",
    [
        # NB: Mistune 0.x and mistune 2.x behave differently with
        # respect to how much HTML escaping of the ``link`` the
        # renderer is expected to do.  Do not put HTML-escaping tests
        # here.  Put them in the ``test_integration`` test later in
        # this file.
        ("a", None, "text", r'<a href="a/">text</a>\Z'),
        ("missing", None, "text", r'<a href="missing">text</a>\Z'),
        ("/", "T", "text", r'<a href="../" title="T">text</a>\Z'),
        ("a&amp;b", None, "x", r'.* href="a&amp;b"'),
        ("/", "<title>", "x", r'.* title="&lt;title&gt;"'),
    ],
)
@pytest.mark.usefixtures("renderer_context")
def test_ImprovedRenderer_link(link, title, text, expected, improved_renderer):
    if MISTUNE_VERSION.startswith("2."):
        result = improved_renderer.link(link, text, title)
    else:
        result = improved_renderer.link(link, title, text)
    assert re.match(expected, result)


@pytest.mark.parametrize(
    "src, title, alt, expected",
    [
        # NB: Mistune 0.x and mistune 2.x behave differently with
        # respect to how much HTML escaping of the ``src`` the
        # renderer is expected to do.  Do not put HTML-escaping tests
        # here.  Put them in the ``test_integration`` test later in
        # this file.
        ("/test.jpg", None, "text", r'<img src="../test.jpg" alt="text"\s*/?>\Z'),
        ("/test.jpg", "T", "x", r'.* title="T"'),
        ("&amp;c.gif", None, "x", r'.* src="&amp;c.gif"'),
        ("/test.jpg", "<title>", "x", r'.* title="&lt;title&gt;"'),
        ("/test.jpg", None, "x&y", r'.* alt="x&amp;y"'),
    ],
)
@pytest.mark.usefixtures("renderer_context")
def test_ImprovedRenderer_image(src, title, alt, expected, improved_renderer):
    if MISTUNE_VERSION.startswith("2."):
        result = improved_renderer.image(src, alt, title)
    else:
        result = improved_renderer.image(src, title, alt)
    assert re.match(expected, result.rstrip())


def test_make_markdown(env):
    with pytest.deprecated_call():
        md = make_markdown(env)
    assert md("foo").strip() == "<p>foo</p>"


@pytest.mark.usefixtures("context")
def test_markdown_to_html(record, field_options):
    with pytest.deprecated_call():
        result = markdown_to_html("goober", record, field_options)
    assert result.html.rstrip() == "<p>goober</p>"


class LinkCounterPlugin(Plugin):
    """A test plugin to test the renderer meta system."""

    name = "LinkCounter"

    class RendererMixin:
        def link(self, *args, **kwargs):
            multiplier = int(self.lektor.field_options.get("multiplier", 1))
            self.lektor.meta["nlinks"] += multiplier
            return super().link(*args, **kwargs)

    def on_markdown_config(self, config, **kwargs):
        config.renderer_mixins.append(self.RendererMixin)

    def on_markdown_meta_init(self, meta, **kwargs):
        # pylint: disable=no-self-use
        meta["nlinks"] = 0


@pytest.fixture
def link_counter_plugin(env):
    env.plugin_controller.instanciate_plugin("link-counter", LinkCounterPlugin)


class TestMarkdown:
    # pylint: disable=no-self-use

    @pytest.fixture
    def source(self):
        return "text"

    @pytest.fixture
    def markdown(self, source, record, field_options):
        return Markdown(source, record, field_options)

    @pytest.mark.parametrize("source, expected", [("x", True), ("", False)])
    def test_bool(self, markdown, source, expected):
        assert bool(markdown) is expected

    def test_record(self, markdown, record):
        assert markdown.record is record

    def test_record_gone_away(self, field_options, mocker):
        markdown = Markdown("text", mocker.Mock(name="record"), field_options)
        with pytest.raises(RuntimeError) as exc_info:
            markdown.record  # pylint: disable=pointless-statement
        assert "gone away" in str(exc_info.value)

    @pytest.mark.parametrize("source", ["![test](/test.jpg)"])
    def test_render_caching(self, markdown, context):
        render1 = markdown._Markdown__render()
        assert '<img src="../test.jpg"' in render1.html
        with context.changed_base_url("/"):
            render2 = markdown._Markdown__render()
            assert '<img src="test.jpg"' in render2.html
        render3 = markdown._Markdown__render()
        assert render3 is render1

    @pytest.mark.parametrize(
        "source, nlinks",
        [
            ("howdy", 0),
            ("[howdy](http://example.com/)", 1),
        ],
    )
    @pytest.mark.usefixtures("context", "link_counter_plugin")
    def test_meta(self, markdown, nlinks):
        assert markdown.meta["nlinks"] == nlinks

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


def _normalize_html(output: Union[str, Markup]) -> str:
    html = str(output).strip()
    html = html.replace("&copy;", "©")
    html = re.sub(r"(<img [^>]*?)\s*/>", r"\1>", html)
    return html


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
        # FIXME: which of these is right?
        ("![](x<br>y.gif)", r'.*<img\b[^>]* src="x(&lt;br&gt;|%3Cbr%3E)y.gif"'),
    ],
)
@pytest.mark.usefixtures("context")
def test_integration(record, field_options, source, expected):
    rendered = _normalize_html(Markdown(source, record, field_options))
    assert re.match(expected, rendered)


@pytest.mark.usefixtures("context", "link_counter_plugin")
def test_field_options_integration(record, field_options):
    # tests that we can pass field options to a custom renderer mixin
    field_options = dict(field_options, multiplier="11")
    two_links = "[one](x.html), [two](y.html)"
    markdown = Markdown(two_links, record, field_options)
    assert markdown.meta["nlinks"] == 22
