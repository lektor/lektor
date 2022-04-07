from warnings import warn

from lektor.markdown import Markdown
from lektor.types.base import Type


class MarkdownDescriptor:
    def __init__(self, source, options):
        self.source = source
        self.options = options

    def __get__(self, obj, type=None):
        if obj is None:
            return self
        return Markdown(self.source, record=obj, field_options=self.options)


class MarkdownType(Type):
    widget = "multiline-text"

    def __init__(self, env, options):
        super().__init__(env, options)
        _check_option(options, "resolve_links", ("always", "never", "when-possible"))

    def value_from_raw(self, raw):
        return MarkdownDescriptor(raw.value or "", self.options)


def _check_option(options, name, choices):
    value = options.get(name)
    if value is not None and value not in choices:
        warn(
            f"Unrecognized value {value!r} for the {name!r} markdown field option. "
            f"Valid values are: {', '.join(repr(_) for _ in choices)}."
        )
