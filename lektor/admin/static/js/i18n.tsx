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

export type Translatable = Partial<Record<string, string>> | string;

/**
 * Get translation for a key.
 * @param key - The translation key.
 */
export function trans(key: Translatable): string {
  if (typeof key === "object") {
    return key[currentLanguage] ?? key.en ?? "";
  }
  return currentTranslations[key] ?? key;
}

/**
 * Get translation for a key with a fallback.
 * @param key - The translation key
 * @param fallback - A fallback to use if the translation is missing.
 */
export function trans_fallback(
  key: Translatable | undefined,
  fallback: string
): string {
  if (!key) {
    return fallback;
  }
  return trans(key) || fallback;
}

/**
 * Get translation for a key with a `%s` replacement.
 * @param key - The translation key
 * @param replacement - replacement for `%s`.
 */
export function trans_format(key: Translatable, replacement: string): string {
  const translation = trans(key);
  return translation.replace("%s", replacement);
}
