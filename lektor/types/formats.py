from lektor.types import Type
from lektor.markdown import Markdown


class MarkdownType(Type):

    def value_from_raw(self, raw):
        if raw.value is None:
            return raw.missing_value('Missing markdown')
        return Markdown(raw.value)
