from datetime import date

from markupsafe import Markup

from lektor.types import Type
from lektor.environment import PRIMARY_ALT
from lektor.utils import bool_from_string
from lektor.i18n import get_i18n_block


class SingleInputType(Type):

    def to_json(self, pad, record=None, alt=PRIMARY_ALT):
        rv = Type.to_json(self, pad, record, alt)
        rv['addon_label_i18n'] = get_i18n_block(
            self.options, 'addon_label') or None
        return rv


class StringType(SingleInputType):

    def value_from_raw(self, raw):
        if raw.value is None:
            return raw.missing_value('Missing string')
        try:
            return raw.value.splitlines()[0].strip()
        except IndexError:
            return u''


class StringsType(Type):

    def value_from_raw(self, raw):
        return [x.strip() for x in (raw.value or '').splitlines()]


class TextType(Type):

    def value_from_raw(self, raw):
        if raw.value is None:
            return raw.missing_value('Missing text')
        return raw.value


class HtmlType(Type):

    def value_from_raw(self, raw):
        if raw.value is None:
            return raw.missing_value('Missing HTML')
        return Markup(raw.value)


class IntegerType(SingleInputType):

    def value_from_raw(self, raw):
        if raw.value is None:
            return raw.missing_value('Missing integer value')
        try:
            return int(raw.value.strip())
        except ValueError:
            try:
                return int(float(raw.value.strip()))
            except ValueError:
                return raw.bad_value('Not an integer')


class FloatType(SingleInputType):

    def value_from_raw(self, raw):
        if raw.value is None:
            return raw.missing_value('Missing float value')
        try:
            return float(raw.value.strip())
        except ValueError:
            return raw.bad_value('Not an integer')


class BooleanType(Type):

    def to_json(self, pad, record=None, alt=PRIMARY_ALT):
        rv = Type.to_json(self, pad, record, alt)
        rv['checkbox_label_i18n'] = get_i18n_block(
            self.options, 'checkbox_label')
        return rv

    def value_from_raw(self, raw):
        if raw.value is None:
            return raw.missing_value('Missing boolean')
        val = bool_from_string(raw.value.strip().lower())
        if val is None:
            return raw.bad_value('Bad boolean value')
        return val


class DateType(SingleInputType):

    def value_from_raw(self, raw):
        if raw.value is None:
            return raw.missing_value('Missing date')
        try:
            return date(*map(int, raw.value.split('-')))
        except Exception:
            return raw.bad_value('Bad date format')
