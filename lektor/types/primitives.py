import re
from datetime import date
from datetime import datetime

from babel.dates import get_timezone
from markupsafe import Markup

from lektor.constants import PRIMARY_ALT
from lektor.i18n import get_i18n_block
from lektor.types.base import Type
from lektor.utils import bool_from_string


class SingleInputType(Type):
    widget = "singleline-text"

    def to_json(self, pad, record=None, alt=PRIMARY_ALT):
        rv = Type.to_json(self, pad, record, alt)
        rv["addon_label_i18n"] = get_i18n_block(self.options, "addon_label") or None
        return rv


class StringType(SingleInputType):
    def value_from_raw(self, raw):
        if raw.value is None:
            return raw.missing_value("Missing string")
        try:
            return raw.value.splitlines()[0].strip()
        except IndexError:
            return ""


class StringsType(Type):
    widget = "multiline-text"

    def value_from_raw(self, raw):
        return [x.strip() for x in (raw.value or "").splitlines()]


class TextType(Type):
    widget = "multiline-text"

    def value_from_raw(self, raw):
        if raw.value is None:
            return raw.missing_value("Missing text")
        return raw.value


class HtmlType(Type):
    widget = "multiline-text"

    def value_from_raw(self, raw):
        if raw.value is None:
            return raw.missing_value("Missing HTML")
        return Markup(raw.value)


class IntegerType(SingleInputType):
    widget = "integer"

    def value_from_raw(self, raw):
        if raw.value is None:
            return raw.missing_value("Missing integer value")
        try:
            return int(raw.value.strip())
        except ValueError:
            try:
                return int(float(raw.value.strip()))
            except ValueError:
                return raw.bad_value("Not an integer")


class FloatType(SingleInputType):
    widget = "float"

    def value_from_raw(self, raw):
        if raw.value is None:
            return raw.missing_value("Missing float value")
        try:
            return float(raw.value.strip())
        except ValueError:
            return raw.bad_value("Not an integer")


class BooleanType(Type):
    widget = "checkbox"

    def to_json(self, pad, record=None, alt=PRIMARY_ALT):
        rv = Type.to_json(self, pad, record, alt)
        rv["checkbox_label_i18n"] = get_i18n_block(self.options, "checkbox_label")
        return rv

    def value_from_raw(self, raw):
        if raw.value is None:
            return raw.missing_value("Missing boolean")
        val = bool_from_string(raw.value.strip().lower())
        if val is None:
            return raw.bad_value("Bad boolean value")
        return val


class DateType(SingleInputType):
    widget = "datepicker"

    def value_from_raw(self, raw):
        if raw.value is None:
            return raw.missing_value("Missing date")
        try:
            return date(*map(int, raw.value.split("-")))
        except Exception:
            return raw.bad_value("Bad date format")


class DateTimeType(SingleInputType):
    widget = "singleline-text"

    def value_from_raw(self, raw):
        if raw.value is None:
            return raw.missing_value("Missing datetime")

        # The previous version of this code allowed a timezone name, followed by a zone
        # offset. In that case the zone name would be ignored (unless the combined zone
        # name, including the offset, matched an IANA zone key). For the sake of
        # backwards compatibility we do the same here.
        m = re.match(
            r"""
            (?P<datetime>
                \d{4} - \d\d? - \d\d?  # YY-MM-DD
                \s+ \d\d? : \d\d (?P<seconds> :\d\d )? # HH:MM[:SS]
            )
            (?: \s+
                (?P<timezone>
                    # Long timezone keys, and — on Windows — names containing
                    # certain characters (those that are not allowed in filenames)
                    # give zoneinfo gas.
                    # https://github.com/python/cpython/issues/96463
                    [^<>:"|?*\x00-\x1f]{,100}?
                    (?P<zoneoffset> [-+] \d\d (?: :? \d\d ){1,2} )?  # ±HHMM[SS]
                )
            )?
            \Z""",
            raw.value.strip(),
            re.DOTALL | re.VERBOSE,
        )
        if m is None:
            return raw.bad_value("Bad datetime format")
        timezone, zoneoffset = m.group("timezone", "zoneoffset")
        tz = None
        if timezone is not None:
            try:
                tz = get_timezone(timezone)
                zoneoffset = None
            except LookupError:
                if zoneoffset is None:
                    return raw.bad_value(f"Unknown timezone {timezone!r}")

        dt = m["datetime"]
        fmt = "%Y-%m-%d %H:%M"
        if m["seconds"] is not None:
            fmt += ":%S"
        if zoneoffset is not None:
            dt += f" {zoneoffset}"
            fmt += " %z"
        try:
            result = datetime.strptime(dt, fmt)
        except ValueError:
            return raw.bad_value("Invalid datetime")

        if tz is None:
            return result

        # as of babel 2.12, get_timezone can return either a pytz timezone
        # or a zoneinfo timezone
        assert result.tzinfo is None
        if hasattr(tz, "localize"):  # pytz
            return tz.localize(result)
        return result.replace(tzinfo=tz)
