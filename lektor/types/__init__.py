from lektor.types.base import BadValue  # noqa - reexport
from lektor.types.base import get_undefined_info  # noqa - reexport
from lektor.types.base import RawValue  # noqa - reexport
from lektor.types.base import Type  # noqa - reexport
from lektor.types.fake import HeadingType
from lektor.types.fake import InfoType
from lektor.types.fake import LineType
from lektor.types.fake import SpacingType
from lektor.types.flow import FlowType
from lektor.types.formats import MarkdownType
from lektor.types.multi import CheckboxesType
from lektor.types.multi import SelectType
from lektor.types.primitives import BooleanType
from lektor.types.primitives import DateTimeType
from lektor.types.primitives import DateType
from lektor.types.primitives import FloatType
from lektor.types.primitives import HtmlType
from lektor.types.primitives import IntegerType
from lektor.types.primitives import StringsType
from lektor.types.primitives import StringType
from lektor.types.primitives import TextType
from lektor.types.special import SlugType
from lektor.types.special import SortKeyType
from lektor.types.special import UrlType


builtin_types = {
    # Primitive
    "string": StringType,
    "strings": StringsType,
    "text": TextType,
    "html": HtmlType,
    "integer": IntegerType,
    "float": FloatType,
    "boolean": BooleanType,
    "date": DateType,
    "datetime": DateTimeType,
    # Multi
    "checkboxes": CheckboxesType,
    "select": SelectType,
    # Special
    "sort_key": SortKeyType,
    "slug": SlugType,
    "url": UrlType,
    # Formats
    "markdown": MarkdownType,
    # Flow
    "flow": FlowType,
    # Fake
    "line": LineType,
    "spacing": SpacingType,
    "info": InfoType,
    "heading": HeadingType,
}
