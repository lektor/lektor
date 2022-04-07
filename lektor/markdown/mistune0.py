"""MarkdownController implementation for mistune 0.x"""
import threading
from typing import ClassVar
from typing import List
from typing import Optional

import mistune  # type: ignore[import]
from deprecated import deprecated

from lektor.markdown.controller import MarkdownController
from lektor.markdown.controller import Meta  # FIXME: move this?
from lektor.markdown.controller import RendererHelper
from lektor.sourceobj import SourceObject


def _escape(text: str) -> str:
    return mistune.escape(text, quote=True)


class ImprovedRenderer(
    # pylint: disable=no-member
    mistune.Renderer  # type: ignore[misc]
):
    lektor: ClassVar = RendererHelper()

    @property  # type: ignore[misc] # https://github.com/python/mypy/issues/1362
    @deprecated("Use ImprovedRenderer.lektor.record instead.")
    def record(self) -> SourceObject:
        return self.lektor.record

    @property  # type: ignore[misc]
    @deprecated("Use ImprovedRenderer.lektor.meta instead.")
    def meta(self) -> Meta:
        return self.lektor.meta

    def link(self, link: str, title: Optional[str], text: str) -> str:
        url = self.lektor.resolve_url(link)
        if not title:
            return f'<a href="{_escape(url)}">{text}</a>'
        return f'<a href="{_escape(url)}" title="{_escape(title)}">{text}</a>'

    def image(self, src: str, title: Optional[str], text: str) -> str:
        url = _escape(self.lektor.resolve_url(src))
        if not title:
            return f'<img src="{url}" alt="{_escape(text)}">'
        return f'<img src="{url}" alt="{_escape(text)}" title="{_escape(title)}">'


class MarkdownConfig:
    def __init__(self) -> None:
        self.options = {
            "escape": False,
        }
        self.renderer_base = ImprovedRenderer
        self.renderer_mixins: List[type] = []

    def make_renderer(self) -> ImprovedRenderer:
        bases = tuple(self.renderer_mixins) + (self.renderer_base,)
        renderer_cls = type("renderer_cls", bases, {})
        return renderer_cls(**self.options)


class MarkdownController0(MarkdownController, threading.local):
    # NB: making this a threading.local means the results in the
    # cached_property MarkdownController.parser having a separate
    # value in each thread.
    #
    # We need that since the mistune 0.x parser is not thread-safe.

    def make_parser(self) -> mistune.Markdown:
        env = self.env
        cfg = MarkdownConfig()
        env.plugin_controller.emit("markdown-config", config=cfg)
        renderer = cfg.make_renderer()
        env.plugin_controller.emit(
            "markdown-lexer-config", config=cfg, renderer=renderer
        )
        # pylint: disable=unexpected-keyword-arg
        return mistune.Markdown(renderer, **cfg.options)
