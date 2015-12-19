// this modules is re-used in the lektor gui system, so be careful with
// imports here.

'use strict';

function loadTranslations() {
  var ctx = require.context('../../../translations', true, /\.json$/);
  var rv = {};
  ctx.keys().forEach((key) => {
    var langIdMatch = key.match(/([a-z]+)/);
    rv[langIdMatch[1]] = ctx(key);
  });
  return rv;
}

var i18n = {
  translations: loadTranslations(),

  currentLanguage: 'en',

  setLanguageFromLocale: function(locale) {
    if (locale) {
      let lang = locale.split(/[-_]/)[0].toLowerCase();
      if (this.translations[lang] !== undefined) {
        this.currentLanguage = lang;
      }
    }
  },

  trans: function(key) {
    var rv;
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


module.exports = i18n;
