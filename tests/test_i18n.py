import importlib

import lektor.i18n


EXPECTED_LANGS = {
    "ca",
    "en",
    "fr",
    "ja",
    "nl",
    "pt",
    "tr",
    "de",
    "es",
    "it",
    "ko",
    "pl",
    "ru",
    "zh",
}


def test_translations_loaded():
    known_langs = set(lektor.i18n.KNOWN_LANGUAGES)
    assert known_langs == EXPECTED_LANGS


def test_loading_i18n_triggers_no_warnings(recwarn):
    importlib.reload(lektor.i18n)
    for warning in recwarn.list:
        print(warning)  # debugging: display warnings on stdout
    assert len(recwarn) == 0
