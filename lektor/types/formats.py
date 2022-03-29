from lektor.markdown import Markdown
from lektor.types.base import Type


class MarkdownDescriptor:
    def __init__(self, source):
        self.source = source

    def __get__(self, obj, type=None):
        if obj is None:
            return self
        return Markdown(self.source, record=obj)


class MarkdownType(Type):
    widget = "multiline-text"

    def value_from_raw(self, raw):
        return MarkdownDescriptor(raw.value or "")
