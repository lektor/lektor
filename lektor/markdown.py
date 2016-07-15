import mistune
import threading
from weakref import ref as weakref

from markupsafe import Markup

from lektor.context import get_ctx
from werkzeug.urls import url_parse


_markdown_cache = threading.local()


class ImprovedRenderer(mistune.Renderer):

    def link(self, link, title, text):
        if self.record is not None:
            url = url_parse(link)
            if not url.scheme:
                link = self.record.url_to('!' + link,
                                          base_url=get_ctx().base_url)
        return mistune.Renderer.link(self, link, title, text)

    def image(self, src, title, text):
        if self.record is not None:
            url = url_parse(src)
            if not url.scheme:
                src = self.record.url_to('!' + src,
                                         base_url=get_ctx().base_url)
        return mistune.Renderer.image(self, src, title, text)


class MarkdownConfig(object):

    def __init__(self):
        self.options = {
            'escape': False,
            'parse_block_html': True,
            'parse_inline_html': True,
        }
        self.renderer_base = ImprovedRenderer
        self.renderer_mixins = []

    def make_renderer(self):
        bases = tuple(self.renderer_mixins) + (self.renderer_base,)
        renderer_cls = type('renderer_cls', bases, {})
        return renderer_cls(**self.options)


def make_markdown(env):
    cfg = MarkdownConfig()
    env.plugin_controller.emit('markdown-config', config=cfg)
    renderer = cfg.make_renderer()
    return mistune.Markdown(renderer, **cfg.options)


def markdown_to_html(text, record=None):
    ctx = get_ctx()
    if ctx is None:
        raise RuntimeError('Context is required for markdown rendering')

    # These markdown parsers are all terrible.  Not one of them does not
    # modify internal state.  So since we only do one of those per thread
    # we can at least cache them on a thread local.
    md = getattr(_markdown_cache, 'md', None)
    if md is None:
        md = make_markdown(ctx.env)
        _markdown_cache.md = md

    meta = {}
    ctx.env.plugin_controller.emit('markdown-meta-init', meta=meta,
                                   record=record)
    md.renderer.meta = meta
    md.renderer.record = record
    rv = md(text)
    ctx.env.plugin_controller.emit('markdown-meta-postprocess', meta=meta,
                                   record=record)
    return rv, meta


class Markdown(object):

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
        if self.__html is None or \
           self.__cached_for_ctx != get_ctx():
            self.__html, self.__meta = markdown_to_html(
                self.source, self.__record())
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

    def __unicode__(self):
        self.__render()
        return self.__html

    def __html__(self):
        self.__render()
        return Markup(self.__html)
