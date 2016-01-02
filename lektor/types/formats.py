from lektor.types import Type
from lektor.markdown import Markdown


class MarkdownType(Type):
    widget = 'multiline-text'

    def value_from_raw(self, raw):
        return Markdown(raw.value or u'')
