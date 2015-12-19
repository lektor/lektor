from lektor.types import Type
from lektor.environment import PRIMARY_ALT
from lektor.i18n import get_i18n_block


class FakeType(Type):

    def value_from_raw(self, raw):
        return None

    def to_json(self, pad, record=None, alt=PRIMARY_ALT):
        rv = Type.to_json(self, pad, record, alt)
        rv['is_fake_type'] = True
        return rv


class LineType(FakeType):
    pass


class SpacingType(FakeType):
    pass


class InfoType(FakeType):
    pass


class HeadingType(FakeType):

    def to_json(self, pad, record=None, alt=PRIMARY_ALT):
        rv = FakeType.to_json(self, pad, record, alt)
        rv['heading_i18n'] = get_i18n_block(self.options, 'heading')
        return rv
