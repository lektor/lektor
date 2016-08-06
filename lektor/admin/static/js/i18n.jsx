function loadTranslations() {
  const ctx = require.context('../../../translations', true, /\.json$/);
  const rv = {};
  ctx.keys().forEach((key) => {
    const langIdMatch = key.match(/([a-z]+)/);
    rv[langIdMatch[1]] = ctx(key);
  });
  return rv
}

const i18n = {
  translations: loadTranslations(),

  currentLanguage: 'en',

  setLanguageFromLocale(locale) {
    if (locale) {
      let lang = locale.split(/[-_]/)[0].toLowerCase();
      if (this.translations[lang] !== undefined) {
        this.currentLanguage = lang;
      }
    }
  },

  trans(key) {
    let rv;
    if (typeof key === 'object') {
      rv = key[i18n.currentLanguage];
      if (rv === undefined) {
        rv = key.en;
      }
      return rv;
    }
    return i18n.translations[i18n.currentLanguage][key] || key;
  }
};


export default i18n
