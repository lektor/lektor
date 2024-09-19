import threading
from abc import ABC
from abc import abstractmethod
from collections.abc import Hashable
from dataclasses import dataclass
from typing import Any
from typing import Callable
from typing import Dict
from typing import Mapping
from typing import MutableMapping
from typing import NamedTuple
from typing import Optional
from typing import TYPE_CHECKING
from weakref import WeakKeyDictionary

from werkzeug.utils import cached_property

from lektor.context import Context
from lektor.context import get_ctx
from lektor.sourceobj import SourceObject

if TYPE_CHECKING:  # pragma: no cover
    from lektor.environment import Environment


@dataclass
class _Threadlocal(threading.local):
    renderer_context: Optional["RendererContext"] = None


_threadlocal = _Threadlocal()

Meta = Dict[str, Any]
FieldOptions = Mapping[str, str]


def require_ctx() -> Context:
    """Get Lektor build context, raising error if there is no current context."""
    ctx = get_ctx()
    if ctx is None:
        raise RuntimeError("Context is required for markdown rendering")
    return ctx


class RendererContext(NamedTuple):
    """Extra data used during Markdown rendering."""

    record: Optional[SourceObject]
    meta: Meta
    field_options: FieldOptions

    def __enter__(self) -> "RendererContext":
        assert _threadlocal.renderer_context is None
        _threadlocal.renderer_context = self
        return self

    def __exit__(self, *__: Any) -> None:
        _threadlocal.renderer_context = None


def get_renderer_context() -> RendererContext:
    if _threadlocal.renderer_context is None:
        raise RuntimeError("RendererContext is required for markdown rendering")
    return _threadlocal.renderer_context


class RendererHelper:
    """Various helpers used by our markdown renderer subclasses."""

    @property
    def record(self) -> Optional[SourceObject]:
        """The record that owns the markdown field being rendered.

        This is used as the base for resolving relative URLs in the Markdown text.
        """
        return get_renderer_context().record

    @property
    def meta(self) -> Meta:
        """The metadata for the current render.

        This is a dict and is used to return metadata from the
        rendering process.  Currently, Lektor itself never generates
        any metadata, but custom Lektor plugins can do so by updating
        this dict.

        Values inserted into this dict during the rendering process
        may be accessed in jinja templates via the ``.meta`` attribute
        of the _markdown_ field.
        """
        return get_renderer_context().meta

    @property
    def field_options(self) -> FieldOptions:
        """Field options.

        A mapping containing the options specified on the markdown field in
        the model.ini file.
        """
        return get_renderer_context().field_options

    @property
    def base_url(self) -> str:
        """Get current base_url from build context.

        The base URL of the artifact being built. This should start
        with a "/", however note that it is interpreted relative to
        any base_path configured for the project.

        """
        return require_ctx().base_url

    def resolve_url(self, url: str) -> str:
        """Resolve markdown link to a URL."""
        resolve_links = self.field_options.get("resolve_links")
        # Default is to resolve links to Lektor source objects when possible
        # This is a change from previous versions where we never resolved
        # links in Markdown.
        record = self.record
        if record is None:
            if resolve_links == "always":
                raise RuntimeError("A source object is required to resolve URLs")
            return url

        resolve = strict_resolve = None
        if resolve_links == "always":
            strict_resolve = True
        elif resolve_links == "never":
            # This is the old behavior, equivalent to '!' prefix
            resolve = False
        return self.record.url_to(
            url, base_url=self.base_url, resolve=resolve, strict_resolve=strict_resolve
        )


class UnknownPluginError(LookupError):
    """Exception raised when a mistune2 plugin name can not be resolved."""


class RenderResult(NamedTuple):
    html: str
    meta: Meta


class MarkdownController(ABC):
    def __init__(self, env: "Environment") -> None:
        self.env = env

    @abstractmethod
    def make_parser(self) -> Callable[[str], str]:  # () -> mistune.Mistune
        """Construct a mistune parser"""

    @cached_property
    def parser(self) -> Callable[[str], str]:  # () -> mistune.Mistune
        return self.make_parser()

    def get_cache_key(self) -> Optional[Hashable]:
        """Get cache key.

        Identical keys guarantee that the rendered result for a given string,
        record, and set of field options will be identical.

        This method may return ``None`` to disable caching of results.
        """
        # pylint: disable=no-self-use
        ctx = get_ctx()
        if ctx is None:
            return None
        return ctx.base_url

    def render(
        self, source: str, record: Optional[SourceObject], field_options: FieldOptions
    ) -> RenderResult:
        """Render markdown string"""
        meta: Meta = {}
        self.env.plugin_controller.emit("markdown-meta-init", meta=meta, record=record)
        with RendererContext(record, meta, field_options):
            html = self.parser(source)
        self.env.plugin_controller.emit(
            "markdown-meta-postprocess", meta=meta, record=record
        )
        return RenderResult(html, meta)


class ControllerCache:
    """Helper for constructing MarkdownControllers thats ensures just one
    controller per Lektor Environment."""

    _cache: MutableMapping["Environment", MarkdownController]

    def __init__(self, factory: Callable[["Environment"], MarkdownController]):
        self.controller_class = factory
        self._cache = WeakKeyDictionary()

    def __call__(self, env: Optional["Environment"] = None) -> MarkdownController:
        """Get MarkdownController for environment.

        If no value is passed for env, the env for the current Lektor build context
        will be used.
        """
        if env is None:
            env = require_ctx().env
        try:
            return self._cache[env]
        except KeyError:
            return self._cache.setdefault(env, self.controller_class(env))
