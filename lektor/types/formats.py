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

    def value_from_raw(self, raw):
        return MarkdownDescriptor(raw.value or u"", self.options)
