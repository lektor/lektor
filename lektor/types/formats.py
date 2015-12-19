import mistune
import threading

from markupsafe import Markup

from lektor.types import Type
from lektor.context import get_ctx


_markdown_cache = threading.local()


class MarkdownConfig(object):

    def __init__(self):
        self.options = {}
        self.renderer_base = mistune.Renderer
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


def markdown_to_html(text):
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
    ctx.env.plugin_controller.emit('markdown-meta-init', meta=meta)
    md.renderer.meta = meta
    rv = md(text)
    ctx.env.plugin_controller.emit('markdown-meta-postprocess', meta=meta)
    return rv, meta


class Markdown(object):

    def __init__(self, source):
        self.source = source
        self.__html = None
        self.__meta = None

    def __render(self):
        if self.__html is None:
            self.__html, self.__meta = markdown_to_html(self.source)

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


class MarkdownType(Type):

    def value_from_raw(self, raw):
        if raw.value is None:
            return raw.missing_value('Missing markdown')
        return Markdown(raw.value)
