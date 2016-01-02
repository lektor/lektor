from lektor.utils import slugify, Url
from lektor.types.primitives import SingleInputType


class SortKeyType(SingleInputType):
    widget = 'integer'

    def value_from_raw(self, raw):
        if raw.value is None:
            return raw.missing_value('Missing sort key')
        try:
            return int(raw.value.strip())
        except ValueError:
            return raw.bad_value('Bad sort key value')


class SlugType(SingleInputType):
    widget = 'slug'

    def value_from_raw(self, raw):
        if raw.value is None:
            return raw.missing_value('Missing slug')
        return slugify(raw.value)


class UrlType(SingleInputType):
    widget = 'url'

    def value_from_raw(self, raw):
        if raw.value is None:
            return raw.missing_value('Missing URL')
        return Url(raw.value)
