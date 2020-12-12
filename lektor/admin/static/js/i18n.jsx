function loadTranslations() {
  const ctx = require.context("../../../translations", true, /\.json$/);
  const rv = {};
  ctx.keys().forEach((key) => {
    const langIdMatch = key.match(/([a-z]+)/);
    rv[langIdMatch[1]] = ctx(key);
  });
  return rv;
}

const translations = loadTranslations();

let currentLanguage = "en";

export function setCurrentLanguage(lang) {
  currentLanguage = lang;
}

export function getCurrentLanguge() {
  return currentLanguage;
}

export function trans(key) {
  let rv;
  if (typeof key === "object") {
    rv = key[currentLanguage];
    if (rv === undefined) {
      rv = key.en;
    }
    return rv;
  }
  return translations[currentLanguage][key] || key;
}
