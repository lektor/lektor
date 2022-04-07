import sys
from typing import Any
from typing import Dict
from typing import Hashable
from typing import Type
from typing import TYPE_CHECKING
from weakref import ref as weakref

from deprecated import deprecated
from markupsafe import Markup

from lektor.markdown.controller import ControllerCache
from lektor.markdown.controller import FieldOptions
from lektor.markdown.controller import MarkdownController
from lektor.markdown.controller import Meta
from lektor.markdown.controller import RenderResult
from lektor.sourceobj import SourceObject

if sys.version_info >= (3, 8):
    from importlib.metadata import version
else:
    from importlib_metadata import version

if TYPE_CHECKING:  # pragma: no cover
    from lektor.environment import Environment


controller_class: Type[MarkdownController]

MISTUNE_VERSION = version("mistune")
if MISTUNE_VERSION.startswith("0."):
    from lektor.markdown.mistune0 import MarkdownController0 as controller_class
elif MISTUNE_VERSION.startswith("2."):
    from lektor.markdown.mistune2 import MarkdownController2 as controller_class
else:  # pragma: no cover
    raise ImportError("Unsupported version of mistune")


get_controller = ControllerCache(controller_class)


@deprecated
def make_markdown(env: "Environment") -> Any:  # (Environment) -> mistune.Markdown
    return get_controller(env).make_parser()


@deprecated
def markdown_to_html(
    text: str, record: SourceObject, field_options: FieldOptions
) -> RenderResult:
    return get_controller().render(text, record, field_options)


class Markdown:
    def __init__(
        self, source: str, record: SourceObject, field_options: FieldOptions
    ) -> None:
        self.source = source
        self.__record = weakref(record)
        self.__field_options = field_options
        self.__cache: Dict[Hashable, RenderResult] = {}

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
        # When the markdown instance is attached to a cached object we
        # can end up in the situation where, e.g., the base_url has
        # changed from the time we were put into the cache to the time
        # where we got referenced by something elsewhere.  Since this
        # affects the processing of relative links, in that case we
        # need to re-process our markdown.
        controller = get_controller()
        key = controller.get_cache_key()
        result = self.__cache.get(key) if key is not None else None
        if result is None:
            result = controller.render(self.source, self.record, self.__field_options)
            if key is not None:
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
