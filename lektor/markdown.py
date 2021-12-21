import threading
from weakref import ref as weakref

import mistune
from markupsafe import escape
from markupsafe import Markup
from werkzeug.urls import url_parse

from lektor.context import get_ctx


_markdown_cache = threading.local()

_old_mistune = int(mistune.__version__.split(".", maxsplit=1)[0]) < 2

if _old_mistune:

    class ImprovedRenderer(mistune.Renderer):
        def link(self, link, title, text):
            return _render_link(link, text, title, record=self.record)

        def image(self, src, title, text):
            return _render_image(src, text, title, record=self.record)

else:

    class ImprovedRenderer(mistune.HTMLRenderer):
        def link(self, link, text=None, title=None):
            return _render_link(link, text, title, record=self.record)

        def image(self, src, alt=None, title=None):
            return _render_image(src, alt, title, record=self.record)


def _render_link(link, text=None, title=None, record=None):
    if record is not None:
        url = url_parse(link)
        if not url.scheme:
            link = record.url_to("!" + link, base_url=get_ctx().base_url)
    link = escape(link)
    if not title:
        return '<a href="%s">%s</a>' % (link, text)
    title = escape(title)
    return '<a href="%s" title="%s">%s</a>' % (link, title, text)


def _render_image(src, alt="", title=None, record=None):
    if record is not None:
        url = url_parse(src)
        if not url.scheme:
            src = record.url_to("!" + src, base_url=get_ctx().base_url)
    src = escape(src)
    alt = escape(alt)
    if title:
        title = escape(title)
        return '<img src="%s" alt="%s" title="%s">' % (src, alt, title)
    return '<img src="%s" alt="%s">' % (src, alt)


class MarkdownConfig:
    def __init__(self):
        self.options = {
            "escape": False,
        }
        self.renderer_base = ImprovedRenderer
        self.renderer_mixins = []

    def make_renderer(self):
        bases = tuple(self.renderer_mixins) + (self.renderer_base,)
        renderer_cls = type("renderer_cls", bases, {})
        return renderer_cls(**self.options)


def make_markdown(env):
    cfg = MarkdownConfig()
    env.plugin_controller.emit("markdown-config", config=cfg)
    renderer = cfg.make_renderer()
    env.plugin_controller.emit("markdown-lexer-config", config=cfg, renderer=renderer)
    if _old_mistune:
        return mistune.Markdown(renderer, **cfg.options)
    return mistune.create_markdown(renderer=renderer, **cfg.options)


def markdown_to_html(text, record=None):
    ctx = get_ctx()
    if ctx is None:
        raise RuntimeError("Context is required for markdown rendering")

    # These markdown parsers are all terrible.  Not one of them does not
    # modify internal state.  So since we only do one of those per thread
    # we can at least cache them on a thread local.
    md = getattr(_markdown_cache, "md", None)
    if md is None:
        md = make_markdown(ctx.env)
        _markdown_cache.md = md

    meta = {}
    ctx.env.plugin_controller.emit("markdown-meta-init", meta=meta, record=record)
    md.renderer.meta = meta
    md.renderer.record = record
    rv = md(text)
    ctx.env.plugin_controller.emit(
        "markdown-meta-postprocess", meta=meta, record=record
    )
    return rv, meta


class Markdown:
    def __init__(self, source, record=None):
        self.source = source
        self.__record = weakref(record) if record is not None else lambda: None
        self.__cached_for_ctx = None
        self.__html = None
        self.__meta = None

    def __bool__(self):
        return bool(self.source)

    __nonzero__ = __bool__

    def __render(self):
        # When the markdown instance is attached to a cached object we can
        # end up in the situation where the context changed from the time
        # we were put into the cache to the time where we got referenced
        # by something elsewhere.  In that case we need to re-process our
        # markdown.  For instance this affects relative links.
        if self.__html is None or self.__cached_for_ctx != get_ctx():
            self.__html, self.__meta = markdown_to_html(self.source, self.__record())
            self.__cached_for_ctx = get_ctx()

    @property
    def meta(self):
        self.__render()
        return self.__meta

    @property
    def html(self):
        self.__render()
        return Markup(self.__html)

    def __getitem__(self, name):
        return self.meta[name]

    def __str__(self):
        self.__render()
        return self.__html

    def __html__(self):
        self.__render()
        return Markup(self.__html)
