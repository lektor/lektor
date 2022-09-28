"""MarkdownController implementation for mistune 2.x"""
from __future__ import annotations

import sys
from importlib import import_module
from typing import Any
from typing import Callable
from typing import ClassVar
from typing import Dict
from typing import List
from typing import Optional
from typing import Sequence

import mistune  # type: ignore[import]

from lektor.markdown.controller import MarkdownController
from lektor.markdown.controller import RendererHelper
from lektor.markdown.controller import UnknownPluginError
from lektor.utils import unique_everseen


class ImprovedRenderer(mistune.HTMLRenderer):  # type: ignore[misc]
    lektor: ClassVar = RendererHelper()

    def link(
        self, link: str, text: Optional[str] = None, title: Optional[str] = None
    ) -> str:
        link = self.lektor.resolve_url(link)
        return super().link(link, text, title)

    def image(self, src: str, alt: str = "", title: Optional[str] = None) -> str:
        src = self.lektor.resolve_url(src)
        return super().image(src, alt, title)


if sys.version_info < (3, 8):
    # No typing.TypedDict → punt
    ParserConfigDict = Dict[str, Any]
else:
    from typing import TypedDict

    class ParserConfigDict(TypedDict, total=False):
        block: mistune.BlockParser
        inline: mistune.InlineParser
        plugins: Sequence[Callable[[mistune.Markdown], None]]


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
        self.renderer_mixins: List[type] = []
        self.parser_options: ParserConfigDict = {
            "plugins": list(self.DEFAULT_PLUGINS),
        }

    def make_renderer(self) -> ImprovedRenderer:
        bases = tuple(self.renderer_mixins) + (self.renderer_base,)
        renderer_cls = type("renderer_cls", bases, {})
        return renderer_cls(**self.renderer_options)


class MarkdownController2(MarkdownController):
    def make_parser(self) -> mistune.Markdown:
        env = self.env
        cfg = MarkdownConfig()
        # FIXME: call different hooks here for mistune 2?
        env.plugin_controller.emit("markdown-config", config=cfg)
        renderer = cfg.make_renderer()
        env.plugin_controller.emit(
            "markdown-lexer-config", config=cfg, renderer=renderer
        )
        parser_options = cfg.parser_options
        plugins = parser_options.get("plugins")
        if plugins:
            # Resolve and filter out duplicates
            parser_options["plugins"] = tuple(
                unique_everseen(map(self.resolve_plugin, plugins))
            )
        return mistune.Markdown(renderer, **cfg.parser_options)

    PLUGINS = {**mistune.PLUGINS}

    def resolve_plugin(self, plugin: str | MistunePlugin) -> MistunePlugin:
        if callable(plugin):
            return plugin
        if not isinstance(plugin, str):
            raise TypeError(
                f"Plugins should be specified as strings or callables, not {plugin!r}"
            )

        module_name, sep, attr = plugin.partition(":")
        if sep:
            try:
                return getattr(import_module(module_name.strip()), attr.strip())
            except (ImportError, AttributeError) as exc:
                raise UnknownPluginError(f"Can not load plugin {plugin!r}") from exc
        try:
            return self.PLUGINS[plugin]
        except KeyError as exc:
            raise UnknownPluginError(f"Unknown plugin {plugin!r}") from exc
