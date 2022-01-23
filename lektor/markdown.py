import threading
from typing import Any
from typing import ClassVar
from typing import Dict
from typing import Hashable
from typing import List
from typing import Mapping
from typing import NamedTuple
from typing import Optional
from typing import Type
from typing import TYPE_CHECKING
from urllib.parse import urlsplit
from weakref import ref as weakref

import mistune  # type: ignore[import]
from deprecated import deprecated
from markupsafe import Markup

from lektor.context import Context
from lektor.context import get_ctx
from lektor.sourceobj import SourceObject

if TYPE_CHECKING:  # pragma: no cover
    from lektor.environment import Environment


_threadlocal = threading.local()
_threadlocal.markdown_cache = {}


def escape(text: str) -> str:
    return mistune.escape(text, quote=True)


Meta = Dict[str, Any]
FieldOptions = Mapping[str, str]


class RendererContext(NamedTuple):
    """Extra data used during Markdown rendering."""

    record: SourceObject
    meta: Meta
    field_options: FieldOptions

    def __enter__(self) -> "RendererContext":
        _threadlocal.renderer_context = self
        return self

    def __exit__(self, typ: Any, value: Any, tb: Any) -> None:
        del _threadlocal.renderer_context


def _require_ctx() -> Context:
    """Get Lektor build context, raising error if there is no current context."""
    ctx = get_ctx()
    if ctx is None:
        raise RuntimeError("Context is required for markdown rendering")
    return ctx


def get_base_url() -> str:
    """Get current base_url from build context.

    The base URL of the artifact being built. This should start with a "/", however
    note that it is interpreted relative to any base_path configured for the project.
    """
    return _require_ctx().base_url


class RenderHelper:
    @property
    def record(self) -> SourceObject:
        """The record that owns the markdown field being rendered.

        This is used as the base for resolving relative URLs in the Markdown text.
        """
        return self.renderer_context.record

    @property
    def meta(self) -> Meta:
        return self.renderer_context.meta

    @property
    def field_options(self) -> FieldOptions:
        """Field options."""
        return self.renderer_context.field_options

    @property
    def renderer_context(self) -> RendererContext:
        return _threadlocal.renderer_context

    def cache_key(self) -> Hashable:
        """Get cache key for rendering.

        This should return a hashable value which is guaranteed to change if the
        rendered value of a given Markdown input string changes.
        """
        # pylint: disable=no-self-use
        return get_base_url()

    def resolve_url(self, url: str) -> str:
        s = urlsplit(url)
        if not (s.scheme or s.netloc or s.query or s.fragment):
            url = "!" + url  # prevent Lektor resolution
        return self.record.url_to(url, base_url=get_base_url())


class ImprovedRenderer(mistune.Renderer):  # type: ignore[misc]

    lektor: ClassVar = RenderHelper()

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
            return f'<a href="{escape(url)}">{text}</a>'
        return f'<a href="{escape(url)}" title="{escape(title)}">{text}</a>'

    def image(self, src: str, title: Optional[str], text: str) -> str:
        url = self.lektor.resolve_url(src)
        if not title:
            return f'<img src="{escape(url)}" alt="{escape(text)}">'
        return f'<img src="{escape(url)}" alt="{escape(text)}" title="{escape(title)}">'


class MarkdownConfig:
    def __init__(self) -> None:
        self.options = {
            "escape": False,
        }
        self.renderer_base: Type[mistune.Renderer] = ImprovedRenderer
        self.renderer_mixins: List[type] = []

    def make_renderer(self) -> mistune.Renderer:
        bases = tuple(self.renderer_mixins) + (self.renderer_base,)
        renderer_cls = type("renderer_cls", bases, {})
        return renderer_cls(**self.options)


def make_markdown(env: "Environment") -> mistune.Markdown:
    cfg = MarkdownConfig()
    env.plugin_controller.emit("markdown-config", config=cfg)
    renderer = cfg.make_renderer()
    env.plugin_controller.emit("markdown-lexer-config", config=cfg, renderer=renderer)
    return mistune.Markdown(renderer, **cfg.options)


def get_markdown_parser(env: "Environment") -> mistune.Markdown:
    """Get Markdown parser, constructing a new one if necessary.

    These parsers are cached, one per thread per env.
    """
    # These markdown parsers are all terrible.  Not one of them does not
    # modify internal state.  So since we only do one of those per thread
    # we can at least cache them on a thread local.
    md = _threadlocal.markdown_cache.get(env)
    if md is None:
        md = make_markdown(env)
        _threadlocal.markdown_cache[env] = md
    return md


class RenderResult(NamedTuple):
    html: str
    meta: Meta


def markdown_to_html(
    text: str, record: SourceObject, field_options: FieldOptions
) -> RenderResult:
    ctx = _require_ctx()
    md = get_markdown_parser(ctx.env)

    meta: Meta = {}
    ctx.env.plugin_controller.emit("markdown-meta-init", meta=meta, record=record)
    with RendererContext(record, meta, field_options):
        rv = md(text)
    ctx.env.plugin_controller.emit(
        "markdown-meta-postprocess", meta=meta, record=record
    )
    return RenderResult(rv, meta)


class Markdown:
    def __init__(
        self, source: str, record: SourceObject, field_options: FieldOptions
    ) -> None:
        self.source = source
        self.__record = weakref(record)
        self.__field_options = field_options
        self.__cache: Dict[str, RenderResult] = {}

    def __bool__(self) -> bool:
        return bool(self.source)

    __nonzero__ = __bool__

    @property
    def record(self) -> SourceObject:
        record = self.__record()
        if record is None:
            raise RuntimeError("Record has gone away")
        return record

    def __render(self) -> RenderResult:
        # When the markdown instance is attached to a cached object we can
        # end up in the situation where the context changed from the time
        # we were put into the cache to the time where we got referenced
        # by something elsewhere.  In that case we need to re-process our
        # markdown.  For instance this affects relative links.
        ctx = _require_ctx()
        md = get_markdown_parser(ctx.env)
        key = md.renderer.lektor.cache_key()
        result = self.__cache.get(key) if key is not None else None
        if result is None:
            result = markdown_to_html(self.source, self.record, self.__field_options)
            self.__cache[key] = result
        return result

    @property
    def meta(self) -> Meta:
        return self.__render().meta

    @property
    def html(self) -> Markup:
        return Markup(self.__render().html)

    def __getitem__(self, name: str) -> Any:
        return self.meta[name]

    def __str__(self) -> str:
        return self.__render().html

    def __html__(self) -> Markup:
        return self.html
