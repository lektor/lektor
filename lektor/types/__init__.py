from jinja2 import Undefined

from lektor.environment import PRIMARY_ALT


class BadValue(Undefined):
    __slots__ = ()


def get_undefined_info(undefined):
    if isinstance(undefined, Undefined):
        try:
            undefined._fail_with_undefined_error()
        except Exception as e:
            return e.message
    return 'defined value'


class RawValue(object):
    __slots__ = ('name', 'value', 'field', 'pad')

    def __init__(self, name, value=None, field=None, pad=None):
        self.name = name
        self.value = value
        self.field = field
        self.pad = pad

    def _get_hint(self, prefix, reason):
        if self.field is not None:
            return '%s in field \'%s\': %s' % (prefix, self.field.name, reason)
        return '%s: %s' % (prefix, reason)

    def bad_value(self, reason):
        return BadValue(hint=self._get_hint('Bad value', reason),
                        obj=self.value)

    def missing_value(self, reason):
        return Undefined(hint=self._get_hint('Missing value', reason),
                         obj=self.value)


class _NameDescriptor(object):

    def __get__(self, obj, type):
        rv = type.__name__
        if rv.endswith('Type'):
            rv = rv[:-4]
        return rv.lower()


class Type(object):
    widget = 'multiline-text'

    def __init__(self, env, options):
        self.env = env
        self.options = options

    @property
    def size(self):
        size = self.options.get('size') or 'normal'
        if size not in ('normal', 'small', 'large'):
            size = 'normal'
        return size

    @property
    def width(self):
        return self.options.get('width') or '1/1'

    name = _NameDescriptor()

    def to_json(self, pad, record=None, alt=PRIMARY_ALT):
        return {
            'name': self.name,
            'widget': self.widget,
            'size': self.size,
            'width': self.width,
        }

    def value_from_raw(self, raw):
        return raw

    def value_from_raw_with_default(self, raw):
        value = self.value_from_raw(raw)
        if isinstance(value, Undefined) and \
           raw.field is not None and \
           raw.field.default is not None:
            return self.value_from_raw(RawValue(raw.name, raw.field.default,
                                                field=raw.field, pad=raw.pad))
        return value

    def __repr__(self):
        return '%s()' % self.__class__.__name__


from lektor.types.primitives import \
     StringType, StringsType, TextType, HtmlType, IntegerType, \
     FloatType, BooleanType, DateType, DateTimeType
from lektor.types.multi import CheckboxesType, SelectType
from lektor.types.special import SortKeyType, SlugType, UrlType
from lektor.types.formats import MarkdownType
from lektor.types.flow import FlowType
from lektor.types.fake import LineType, SpacingType, InfoType, HeadingType


builtin_types = {
    # Primitive
    'string': StringType,
    'strings': StringsType,
    'text': TextType,
    'html': HtmlType,
    'integer': IntegerType,
    'float': FloatType,
    'boolean': BooleanType,
    'date': DateType,
    'datetime': DateTimeType,

    # Multi
    'checkboxes': CheckboxesType,
    'select': SelectType,

    # Special
    'sort_key': SortKeyType,
    'slug': SlugType,
    'url': UrlType,

    # Formats
    'markdown': MarkdownType,

    # Flow
    'flow': FlowType,

    # Fake
    'line': LineType,
    'spacing': SpacingType,
    'info': InfoType,
    'heading': HeadingType,
}
