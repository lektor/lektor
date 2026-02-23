"""MarkdownController implementation for mistune 2.x"""

from __future__ import annotations

import re
from collections.abc import Callable
from collections.abc import Sequence
from typing import ClassVar
from typing import TypedDict

import mistune.util

from lektor.markdown.controller import MarkdownController
from lektor.markdown.controller import RendererHelper
from lektor.markdown.controller import UnknownPluginError
from lektor.utils import unique_everseen


def escape(text: str) -> str:
    # This is only here to provide the implementation for the
    # deprecated lektor.markdown.escape method.
    #
    # (We don't use it below and it can be deleted once access
    # to lektor.markdown.escape is removed.)
    return mistune.util.escape(text, quote=True)


class ImprovedRenderer(mistune.HTMLRenderer):  # type: ignore[misc]
    lektor: ClassVar = RendererHelper()

    # The deprecated .record and .meta attributes are not made available here, since old
    # renderer mixins (written for Lektor<3.4 and mistune 0.x) are not going to work
    # with mistune 2.x anyway.

    def link(self, text: str, url: str, title: str | None = None) -> str:
        url = self.lektor.resolve_url(url)
        return super().link(text, url, title)

    def image(self, text: str, url: str, title: str | None = None) -> str:
        url = self.lektor.resolve_url(url)
        return super().image(text, url, title)


class ParserConfigDict(TypedDict, total=False):
    block: mistune.BlockParser
    inline: mistune.InlineParser
    plugins: Sequence[Callable[[mistune.Markdown], None] | str]


MistunePlugin = Callable[[mistune.Markdown], None]


class MarkdownConfig:
    # Enabling these plugins give us feature parity with mistune 0.8.4.
    # We enable them by default for the sake of backwards-compatibility.
    DEFAULT_PLUGINS = ("url", "strikethrough", "footnotes", "table")

    def __init__(self) -> None:
        self.renderer_options = {
            "escape": False,
            "allow_harmful_protocols": True,
        }
        self.renderer_base = ImprovedRenderer
        self.renderer_mixins: list[type] = []
        self.parser_options: ParserConfigDict = {
            "plugins": list(self.DEFAULT_PLUGINS),
        }

    def make_renderer(self) -> ImprovedRenderer:
        bases = tuple(self.renderer_mixins) + (self.renderer_base,)
        renderer_cls = type("renderer_cls", bases, {})
        return renderer_cls(**self.renderer_options)


class MarkdownController3(MarkdownController):
    def make_parser(self) -> mistune.Markdown:
        env = self.env
        cfg = MarkdownConfig()
        # FIXME: call different hooks here for mistune 3?
        env.plugin_controller.emit("markdown-config", config=cfg)
        renderer = cfg.make_renderer()
        env.plugin_controller.emit(
            "markdown-lexer-config", config=cfg, renderer=renderer
        )
        parser_options = cfg.parser_options
        # FIXME: handle other parser_options.
        # Pass, as appropriate to BlockParser, InlineParser, Renderer
        plugins = parser_options.get("plugins")
        if plugins:
            plugins = tuple(unique_everseen(map(self.resolve_plugin, plugins)))
        return mistune.Markdown(renderer, plugins=plugins)

    def resolve_plugin(self, plugin: str | MistunePlugin) -> MistunePlugin:
        if callable(plugin):
            return plugin
        if not isinstance(plugin, str):
            raise TypeError(
                f"Plugins should be specified as strings or callables, not {plugin!r}"
            )

        # Mistune3 uses '.' instead of ':' to separate module from
        # function name. E.g. instead of `my.module:plugin`, mistune3
        # wants `my.module.plugin`.
        alldots = re.sub(r"(?<=\w) : (?= \w+ \Z)", ".", plugin, flags=re.VERBOSE)
        try:
            return mistune.plugins.import_plugin(alldots)
        except (ImportError, AttributeError, ValueError) as exc:
            raise UnknownPluginError(f"Can not load plugin {plugin!r}") from exc
