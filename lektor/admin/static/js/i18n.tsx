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

export function trans(key: Translatable, fallback?: string): string {
  if (typeof key === "object") {
    return key[currentLanguage] ?? key.en ?? fallback ?? "MISSING TRANSLATION";
  }
  return currentTranslations[key] || key;
}
