from lektor.types import Type
from lektor.markdown import Markdown
from lektor.environment import PRIMARY_ALT


class MarkdownDescriptor(object):

    def __init__(self, source):
        self.source = source

    def __get__(self, obj, type=None):
        if obj is None:
            return self
        return Markdown(self.source, record=obj)


class MarkdownType(Type):
    widget = 'multiline-text'

    def value_from_raw(self, raw):
        return MarkdownDescriptor(raw.value or u'')

class MarkdownGUIType(MarkdownType):
    widget = 'markdown-gui'

    def to_json(self, pad, record=None, alt=PRIMARY_ALT):
        rv = MarkdownType.to_json(self, pad, record, alt)
        default_view = self.options.get('default_view') or 'richtext'
        if default_view not in ('richtext', 'markdown'):
            default_view = 'richtext'
        rv['default_view'] = default_view
        return rv
