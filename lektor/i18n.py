import os
import json

from lektor.uilink import UI_LANG


translations_path = os.path.join(os.path.abspath(os.path.dirname(__file__)),
                            'translations')
KNOWN_LANGUAGES = list(x[:-5] for x in os.listdir(translations_path)
                       if x.endswith('.json'))


translations = {}
for _lang in KNOWN_LANGUAGES:
    with open(os.path.join(translations_path, _lang + '.json')) as f:
        translations[_lang] = json.load(f)


def get_translations(language):
    """Looks up the translations for a given language."""
    return translations.get(language)


def is_valid_language(lang):
    """Verifies a language is known and valid."""
    return lang in KNOWN_LANGUAGES


def get_default_lang():
    """Returns the default language the system should use."""
    if UI_LANG is not None:
        return UI_LANG
    for key in 'LANGUAGE', 'LC_ALL', 'LC_CTYPE', 'LANG':
        value = os.environ.get(key)
        if not value:
            continue
        lang = value.split('_')[0].lower()
        if is_valid_language(lang):
            return lang
    return 'en'


def load_i18n_block(key):
    """Looks up an entire i18n block from a known translation."""
    rv = {}
    for lang in KNOWN_LANGUAGES:
        val = translations.get(lang, {}).get(key)
        if val is not None:
            rv[lang] = val
    return rv


def get_i18n_block(inifile_or_dict, key):
    """Extracts an i18n block from an ini file or dictionary for a given
    key.
    """
    rv = {}
    for k, v in inifile_or_dict.iteritems():
        if k == key:
            # English is the internal default language with preferred
            # treatment.
            rv['en'] = v
        elif k.startswith(key + '['):
            rv[k[len(key) + 1:-1]] = v
    return rv
