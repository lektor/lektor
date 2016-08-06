import {makeRichPromise} from './richPromise'


function slug(string, opts) {
  opts = opts || {};
  string = string.toString();
  if ('string' === typeof opts)
    opts = {replacement:opts};
  opts.mode = opts.mode || slug.defaults.mode;
  const defaults = slug.defaults.modes[opts.mode];
  ['replacement','multicharmap','charmap','remove'].forEach(function (key) {
    opts[key] = opts[key] || defaults[key];
  });
  if ('undefined' === typeof opts.symbols)
    opts.symbols = defaults.symbols;
  const lengths = []
  Object.keys(opts.multicharmap).forEach(function (key) {
    const len = key.length
    if (lengths.indexOf(len) === -1)
      lengths.push(len);
  });
  let code, unicode, result = "";
  for (let char, i = 0, l = string.length; i < l; i++) { char = string[i];
    if (!lengths.some(function (len) {
      const str = string.substr(i, len)
      if (opts.multicharmap[str]) {
        i += len - 1;
        char = opts.multicharmap[str];
        return true;
      } else return false;
    })) {
      if (opts.charmap[char]) {
        char = opts.charmap[char];
        code = char.charCodeAt(0);
      } else {
        code = string.charCodeAt(i);
      }
    }
    char = char.replace(/[^\w\s\-\.\_~]/g, ''); // allowed
    if (opts.remove) char = char.replace(opts.remove, ''); // add flavour
    result += char;
  }
  result = result.replace(/^\s+|\s+$/g, ''); // trim leading/trailing spaces
  result = result.replace(/[-\s]+/g, opts.replacement); // convert spaces
  return result.replace(opts.replacement+"$",''); // remove trailing separator
}

slug.defaults = {
    mode: 'pretty',
};

slug.multicharmap = slug.defaults.multicharmap = {
    '<3': 'love', '&&': 'and', '||': 'or', 'w/': 'with',
};

// https://code.djangoproject.com/browser/django/trunk/django/contrib/admin/media/js/urlify.js
slug.charmap  = slug.defaults.charmap = {
  // latin
  'À': 'A', 'Á': 'A', 'Â': 'A', 'Ã': 'A', 'Ä': 'Ae', 'Å': 'A', 'Æ': 'AE',
  'Ç': 'C', 'È': 'E', 'É': 'E', 'Ê': 'E', 'Ë': 'E', 'Ì': 'I', 'Í': 'I',
  'Î': 'I', 'Ï': 'I', 'Ð': 'D', 'Ñ': 'N', 'Ò': 'O', 'Ó': 'O', 'Ô': 'O',
  'Õ': 'O', 'Ö': 'Oe', 'Ő': 'O', 'Ø': 'O', 'Ù': 'U', 'Ú': 'U', 'Û': 'U',
  'Ü': 'Ue', 'Ű': 'U', 'Ý': 'Y', 'Þ': 'TH', 'ß': 'ss', 'à':'a', 'á':'a',
  'â': 'a', 'ã': 'a', 'ä': 'ae', 'å': 'a', 'æ': 'ae', 'ç': 'c', 'è': 'e',
  'é': 'e', 'ê': 'e', 'ë': 'e', 'ì': 'i', 'í': 'i', 'î': 'i', 'ï': 'i',
  'ð': 'd', 'ñ': 'n', 'ò': 'o', 'ó': 'o', 'ô': 'o', 'õ': 'o', 'ö': 'oe',
  'ő': 'o', 'ø': 'o', 'ù': 'u', 'ú': 'u', 'û': 'u', 'ü': 'ue', 'ű': 'u',
  'ý': 'y', 'þ': 'th', 'ÿ': 'y', 'ẞ': 'SS',
  // greek
  'α':'a', 'β':'b', 'γ':'g', 'δ':'d', 'ε':'e', 'ζ':'z', 'η':'h', 'θ':'8',
  'ι':'i', 'κ':'k', 'λ':'l', 'μ':'m', 'ν':'n', 'ξ':'3', 'ο':'o', 'π':'p',
  'ρ':'r', 'σ':'s', 'τ':'t', 'υ':'y', 'φ':'f', 'χ':'x', 'ψ':'ps', 'ω':'w',
  'ά':'a', 'έ':'e', 'ί':'i', 'ό':'o', 'ύ':'y', 'ή':'h', 'ώ':'w', 'ς':'s',
  'ϊ':'i', 'ΰ':'y', 'ϋ':'y', 'ΐ':'i',
  'Α':'A', 'Β':'B', 'Γ':'G', 'Δ':'D', 'Ε':'E', 'Ζ':'Z', 'Η':'H', 'Θ':'8',
  'Ι':'I', 'Κ':'K', 'Λ':'L', 'Μ':'M', 'Ν':'N', 'Ξ':'3', 'Ο':'O', 'Π':'P',
  'Ρ':'R', 'Σ':'S', 'Τ':'T', 'Υ':'Y', 'Φ':'F', 'Χ':'X', 'Ψ':'PS', 'Ω':'W',
  'Ά':'A', 'Έ':'E', 'Ί':'I', 'Ό':'O', 'Ύ':'Y', 'Ή':'H', 'Ώ':'W', 'Ϊ':'I',
  'Ϋ':'Y',
  // turkish
  'ş':'s', 'Ş':'S', 'ı':'i', 'İ':'I',
  'ğ':'g', 'Ğ':'G',
  // russian
  'а':'a', 'б':'b', 'в':'v', 'г':'g', 'д':'d', 'е':'e', 'ё':'yo', 'ж':'zh',
  'з':'z', 'и':'i', 'й':'j', 'к':'k', 'л':'l', 'м':'m', 'н':'n', 'о':'o',
  'п':'p', 'р':'r', 'с':'s', 'т':'t', 'у':'u', 'ф':'f', 'х':'h', 'ц':'c',
  'ч':'ch', 'ш':'sh', 'щ':'sh', 'ъ':'u', 'ы':'y', 'ь':'', 'э':'e', 'ю':'yu',
  'я':'ya',
  'А':'A', 'Б':'B', 'В':'V', 'Г':'G', 'Д':'D', 'Е':'E', 'Ё':'Yo', 'Ж':'Zh',
  'З':'Z', 'И':'I', 'Й':'J', 'К':'K', 'Л':'L', 'М':'M', 'Н':'N', 'О':'O',
  'П':'P', 'Р':'R', 'С':'S', 'Т':'T', 'У':'U', 'Ф':'F', 'Х':'H', 'Ц':'C',
  'Ч':'Ch', 'Ш':'Sh', 'Щ':'Sh', 'Ъ':'U', 'Ы':'Y', 'Ь':'', 'Э':'E', 'Ю':'Yu',
  'Я':'Ya',
  // ukranian
  'Є':'Ye', 'І':'I', 'Ї':'Yi', 'Ґ':'G', 'є':'ye', 'і':'i', 'ї':'yi', 'ґ':'g',
  // czech
  'č':'c', 'ď':'d', 'ě':'e', 'ň': 'n', 'ř':'r', 'š':'s', 'ť':'t', 'ů':'u',
  'ž':'z', 'Č':'C', 'Ď':'D', 'Ě':'E', 'Ň': 'N', 'Ř':'R', 'Š':'S', 'Ť':'T',
  'Ů':'U', 'Ž':'Z',
  // polish
  'ą':'a', 'ć':'c', 'ę':'e', 'ł':'l', 'ń':'n', 'ś':'s', 'ź':'z',
  'ż':'z', 'Ą':'A', 'Ć':'C', 'Ę':'E', 'Ł':'L', 'Ń':'N', 'Ś':'S',
  'Ź':'Z', 'Ż':'Z',
  // latvian
  'ā':'a', 'ē':'e', 'ģ':'g', 'ī':'i', 'ķ':'k', 'ļ':'l', 'ņ':'n',
  'ū':'u', 'Ā':'A', 'Ē':'E', 'Ģ':'G', 'Ī':'I',
  'Ķ':'K', 'Ļ':'L', 'Ņ':'N', 'Ū':'U',
  // lithuanian
  'ė':'e', 'į':'i', 'ų':'u', 'Ė': 'E', 'Į': 'I', 'Ų':'U',
  // romanian
  'ț':'t', 'Ț':'T', 'ţ':'t', 'Ţ':'T', 'ș':'s', 'Ș':'S', 'ă':'a', 'Ă':'A',
  // currency
  '€': 'euro', '₢': 'cruzeiro', '₣': 'french franc', '£': 'pound',
  '₤': 'lira', '₥': 'mill', '₦': 'naira', '₧': 'peseta', '₨': 'rupee',
  '₩': 'won', '₪': 'new shequel', '₫': 'dong', '₭': 'kip', '₮': 'tugrik',
  '₯': 'drachma', '₰': 'penny', '₱': 'peso', '₲': 'guarani', '₳': 'austral',
  '₴': 'hryvnia', '₵': 'cedi', '¢': 'cent', '¥': 'yen', '元': 'yuan',
  '円': 'yen', '﷼': 'rial', '₠': 'ecu', '¤': 'currency', '฿': 'baht',
  "$": 'dollar', '₹': 'indian rupee',
  // symbols
  '©':'(c)', 'œ': 'oe', 'Œ': 'OE', '∑': 'sum', '®': '(r)', '†': '+',
  '“': '"', '”': '"', '‘': "'", '’': "'", '∂': 'd', 'ƒ': 'f', '™': 'tm',
  '℠': 'sm', '…': '...', '˚': 'o', 'º': 'o', 'ª': 'a', '•': '*',
  '∆': 'delta', '∞': 'infinity', '♥': 'love', '&': 'and', '|': 'or',
  '<': 'less', '>': 'greater', '=': 'equals'
};

slug.defaults.modes = {
  pretty: {
    replacement: '-',
    symbols: true,
    remove: /[.]/g,
    charmap: slug.defaults.charmap,
    multicharmap: slug.defaults.multicharmap,
  }
};


const utils = {
  slugify: slug,

  getCanonicalUrl(localPath) {
    return $LEKTOR_CONFIG.site_root.match(/^(.*?)\/*$/)[1] +
      '/' + utils.stripLeadingSlash(localPath);
  },

  isValidUrl(url) {
    return !!url.match(/^(https?|ftp):\/\/\S+$/);
  },

  stripLeadingSlash(string) {
    return string.match(/^\/*(.*?)$/)[1];
  },

  stripTrailingSlash(string) {
    return string.match(/^(.*?)\/*$/)[1];
  },

  joinFsPath(a, b) {
    return utils.stripTrailingSlash(a) + '/' + utils.stripLeadingSlash(b);
  },

  flipSetValue(originalSet, value, isActive) {
    if (isActive) {
      return utils.addToSet(originalSet || [], value);
    } else {
      return utils.removeFromSet(originalSet || [], value);
    }
  },

  addToSet(originalSet, value) {
    for (let i = 0; i < originalSet.length; i++) {
      if (originalSet[i] === value) {
        return originalSet;
      }
    }
    const rv = originalSet.slice()
    rv.push(value);
    return rv;
  },

  removeFromSet(originalSet, value) {
    let rv = null;
    let off = 0;
    for (let i = 0; i < originalSet.length; i++) {
      if (originalSet[i] === value) {
        if (rv === null) {
          rv = originalSet.slice();
        }
        rv.splice(i - (off++), 1);
      }
    }
    return (rv === null) ? originalSet : rv;
  },

  urlPathsConsideredEqual(a, b) {
    if ((a == null) || (b == null)) {
      return false;
    }
    return utils.stripTrailingSlash(a) == utils.stripTrailingSlash(b);
  },

  fsPathFromAdminObservedPath(adminPath) {
    const base = $LEKTOR_CONFIG.site_root.match(/^(.*?)\/*$/)[1]
    if (adminPath.substr(0, base.length) != base) {
      return null;
    }
    return '/' + adminPath.substr(base.length).match(/^\/*(.*?)\/*$/)[1];
  },

  getParentFsPath(fsPath) {
    return fsPath.match(/^(.*?)\/([^\/]*)$/)[1];
  },

  getApiUrl(url) {
    return $LEKTOR_CONFIG.admin_root + '/api' + url;
  },

  loadData(url, params, options) {
    options = options || {};
    return makeRichPromise((resolve, reject) => {
      jQuery.ajax({
        url: utils.getApiUrl(url),
        data: params,
        method: options.method || 'GET'
      }).done((data) => {
        resolve(data);
      }).fail(() => {
        reject({
          code: 'REQUEST_FAILED'
        });
      });
    });
  },

  apiRequest(url, options) {
    options = options || {};
    options.url = utils.getApiUrl(url);
    if (options.json !== undefined) {
      options.data = JSON.stringify(options.json);
      options.contentType = 'application/json';
      delete options.json;
    }
    if (!options.method) {
      options.method = 'GET';
    }

    return makeRichPromise((resolve, reject) => {
      jQuery.ajax(options)
        .done((data) => {
          resolve(data);
        })
        .fail(() => {
          reject({
            code: 'REQUEST_FAILED'
          });
        });
    });
  },

  fsToUrlPath(fsPath) {
    let segments = fsPath.match(/^\/*(.*?)\/*$/)[1].split('/');
    if (segments.length == 1 && segments[0] == '') {
      segments = [];
    }
    segments.unshift('root');
    return segments.join(':');
  },

  urlToFsPath(urlPath) {
    const segments = urlPath.match(/^:*(.*?):*$/)[1].split(':')
    if (segments.length < 1 || segments[0] != 'root') {
      return null;
    }
    segments[0] = '';
    return segments.join('/');
  },

  urlPathToSegments(urlPath) {
    if (!urlPath) {
      return null;
    }
    const rv = urlPath.match(/^:*(.*?):*$/)[1].split('/')
    if (rv.length >= 1 && rv[0] == 'root') {
      return rv.slice(1);
    }
    return null;
  },

  scrolledToBottom() {
    return document.body.offsetHeight + document.body.scrollTop
      >= document.body.scrollHeight;
  },

  getPlatform() {
    if (navigator.appVersion.indexOf('Win') != -1) {
      return 'windows';
    } else if (navigator.appVersion.indexOf('Mac') != -1) {
      return 'mac';
    } else if (navigator.appVersion.indexOf('X11') != -1 ||
        navigator.appVersion.indexOf('Linux') != -1) {
      return 'linux';
    }
    return 'other';
  },

  isMetaKey(event) {
    if (utils.getPlatform() == 'mac') {
      return event.metaKey;
    } else {
      return event.ctrlKey;
    }
  }
};

export default utils
