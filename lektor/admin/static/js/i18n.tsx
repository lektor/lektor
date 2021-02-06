function loadTranslations() {
  const rv: Record<string, Record<string, string>> = {};
  try {
    const ctx = require.context("../../../translations", true, /\.json$/);
    ctx.keys().forEach((key) => {
      const langIdMatch = key.match(/([a-z]+)/);
      if (langIdMatch) {
        rv[langIdMatch[1]] = ctx(key);
      }
    });
  } catch (err) {
    // require.context is not available when running tests.
  }
  return rv;
}

const translations: Record<string, Record<string, string>> = loadTranslations();

let currentLanguage = "en";
let currentTranslations = translations[currentLanguage];

export function setCurrentLanguage(lang: string) {
  currentLanguage = lang;
  currentTranslations = translations[currentLanguage];
}

export function getCurrentLanguge() {
  return currentLanguage;
}

export type Translatable = Partial<Record<string, string>>;

/**
 * Get translation for a key.
 * @param key - The translation key.
 */
export function trans(key: string): string {
  return currentTranslations[key] ?? key;
}

/**
 * Get translation from an object of translations
 * @param translation_object - The object containing translations.
 */
export function trans_obj(translation_object: Translatable): string {
  return translation_object[currentLanguage] ?? translation_object.en ?? "";
}

/**
 * Get translation for a key with a fallback.
 * @param translation_object - The translation key
 * @param fallback - A fallback to use if the translation is missing.
 */
export function trans_fallback(
  translation_object: Translatable | undefined,
  fallback: string
): string {
  if (!translation_object) {
    return fallback;
  }
  return trans_obj(translation_object) || fallback;
}

/**
 * Get translation for a key with a `%s` replacement.
 * @param key - The translation key
 * @param replacement - replacement for `%s`.
 */
export function trans_format(key: string, replacement: string): string {
  const translation = trans(key);
  return translation.replace("%s", replacement);
}
