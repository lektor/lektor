from datetime import date, datetime

from markupsafe import Markup

from lektor.types import Type
from lektor.environment import PRIMARY_ALT
from lektor.utils import bool_from_string
from lektor.i18n import get_i18n_block

from babel.dates import get_timezone
from pytz import FixedOffset


class SingleInputType(Type):
    widget = 'singleline-text'

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
    widget = 'multiline-text'

    def value_from_raw(self, raw):
        return [x.strip() for x in (raw.value or '').splitlines()]


class TextType(Type):
    widget = 'multiline-text'

    def value_from_raw(self, raw):
        if raw.value is None:
            return raw.missing_value('Missing text')
        return raw.value


class HtmlType(Type):
    widget = 'multiline-text'

    def value_from_raw(self, raw):
        if raw.value is None:
            return raw.missing_value('Missing HTML')
        return Markup(raw.value)


class IntegerType(SingleInputType):
    widget = 'integer'

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
    widget = 'float'

    def value_from_raw(self, raw):
        if raw.value is None:
            return raw.missing_value('Missing float value')
        try:
            return float(raw.value.strip())
        except ValueError:
            return raw.bad_value('Not an integer')


class BooleanType(Type):
    widget = 'checkbox'

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
    widget = 'datepicker'

    def value_from_raw(self, raw):
        if raw.value is None:
            return raw.missing_value('Missing date')
        try:
            return date(*map(int, raw.value.split('-')))
        except Exception:
            return raw.bad_value('Bad date format')


class DateTimeType(SingleInputType):
    widget = 'singleline-text'

    def value_from_raw(self, raw):
        if raw.value is None:
            return raw.missing_value('Missing datetime')
        try:
            chunks = raw.value.split(' ')
            date_info = [int(bit) for bit in chunks[0].split('-')]
            time_info = [int(bit) for bit in chunks[1].split(':')]
            datetime_info = date_info + time_info
            result = datetime(*datetime_info)

            if len(chunks) > 2:
                try:
                    tz = get_timezone(chunks[-1])
                except LookupError:
                    if len(chunks[-1]) > 5:
                        chunks[-1] = chunks[-1][-5:]
                    delta = int(chunks[-1][1:3]) * 60 + int(chunks[-1][3:])
                    if chunks[-1][0] == '-':
                        delta *= -1
                    tz = FixedOffset(delta)
                return tz.localize(result)

            return result
        except Exception:
            return raw.bad_value('Bad date format')
