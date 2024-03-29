// https://code.djangoproject.com/browser/django/trunk/django/contrib/admin/media/js/urlify.js
const charmap: Record<string, string> = {
  // latin
  À: "A",
  Á: "A",
  Â: "A",
  Ã: "A",
  Ä: "Ae",
  Å: "A",
  Æ: "AE",
  Ç: "C",
  È: "E",
  É: "E",
  Ê: "E",
  Ë: "E",
  Ì: "I",
  Í: "I",
  Î: "I",
  Ï: "I",
  Ð: "D",
  Ñ: "N",
  Ò: "O",
  Ó: "O",
  Ô: "O",
  Õ: "O",
  Ö: "Oe",
  Ő: "O",
  Ø: "O",
  Ù: "U",
  Ú: "U",
  Û: "U",
  Ü: "Ue",
  Ű: "U",
  Ý: "Y",
  Þ: "TH",
  ß: "ss",
  à: "a",
  á: "a",
  â: "a",
  ã: "a",
  ä: "ae",
  å: "a",
  æ: "ae",
  ç: "c",
  è: "e",
  é: "e",
  ê: "e",
  ë: "e",
  ì: "i",
  í: "i",
  î: "i",
  ï: "i",
  ð: "d",
  ñ: "n",
  ò: "o",
  ó: "o",
  ô: "o",
  õ: "o",
  ö: "oe",
  ő: "o",
  ø: "o",
  ù: "u",
  ú: "u",
  û: "u",
  ü: "ue",
  ű: "u",
  ý: "y",
  þ: "th",
  ÿ: "y",
  ẞ: "SS",
  // greek
  α: "a",
  β: "b",
  γ: "g",
  δ: "d",
  ε: "e",
  ζ: "z",
  η: "h",
  θ: "8",
  ι: "i",
  κ: "k",
  λ: "l",
  μ: "m",
  ν: "n",
  ξ: "3",
  ο: "o",
  π: "p",
  ρ: "r",
  σ: "s",
  τ: "t",
  υ: "y",
  φ: "f",
  χ: "x",
  ψ: "ps",
  ω: "w",
  ά: "a",
  έ: "e",
  ί: "i",
  ό: "o",
  ύ: "y",
  ή: "h",
  ώ: "w",
  ς: "s",
  ϊ: "i",
  ΰ: "y",
  ϋ: "y",
  ΐ: "i",
  Α: "A",
  Β: "B",
  Γ: "G",
  Δ: "D",
  Ε: "E",
  Ζ: "Z",
  Η: "H",
  Θ: "8",
  Ι: "I",
  Κ: "K",
  Λ: "L",
  Μ: "M",
  Ν: "N",
  Ξ: "3",
  Ο: "O",
  Π: "P",
  Ρ: "R",
  Σ: "S",
  Τ: "T",
  Υ: "Y",
  Φ: "F",
  Χ: "X",
  Ψ: "PS",
  Ω: "W",
  Ά: "A",
  Έ: "E",
  Ί: "I",
  Ό: "O",
  Ύ: "Y",
  Ή: "H",
  Ώ: "W",
  Ϊ: "I",
  Ϋ: "Y",
  // turkish
  ş: "s",
  Ş: "S",
  ı: "i",
  İ: "I",
  ğ: "g",
  Ğ: "G",
  // russian
  а: "a",
  б: "b",
  в: "v",
  г: "g",
  д: "d",
  е: "e",
  ё: "yo",
  ж: "zh",
  з: "z",
  и: "i",
  й: "j",
  к: "k",
  л: "l",
  м: "m",
  н: "n",
  о: "o",
  п: "p",
  р: "r",
  с: "s",
  т: "t",
  у: "u",
  ф: "f",
  х: "h",
  ц: "c",
  ч: "ch",
  ш: "sh",
  щ: "sh",
  ъ: "u",
  ы: "y",
  ь: "",
  э: "e",
  ю: "yu",
  я: "ya",
  А: "A",
  Б: "B",
  В: "V",
  Г: "G",
  Д: "D",
  Е: "E",
  Ё: "Yo",
  Ж: "Zh",
  З: "Z",
  И: "I",
  Й: "J",
  К: "K",
  Л: "L",
  М: "M",
  Н: "N",
  О: "O",
  П: "P",
  Р: "R",
  С: "S",
  Т: "T",
  У: "U",
  Ф: "F",
  Х: "H",
  Ц: "C",
  Ч: "Ch",
  Ш: "Sh",
  Щ: "Sh",
  Ъ: "U",
  Ы: "Y",
  Ь: "",
  Э: "E",
  Ю: "Yu",
  Я: "Ya",
  // ukranian
  Є: "Ye",
  І: "I",
  Ї: "Yi",
  Ґ: "G",
  є: "ye",
  і: "i",
  ї: "yi",
  ґ: "g",
  // czech
  č: "c",
  ď: "d",
  ě: "e",
  ň: "n",
  ř: "r",
  š: "s",
  ť: "t",
  ů: "u",
  ž: "z",
  Č: "C",
  Ď: "D",
  Ě: "E",
  Ň: "N",
  Ř: "R",
  Š: "S",
  Ť: "T",
  Ů: "U",
  Ž: "Z",
  // polish
  ą: "a",
  ć: "c",
  ę: "e",
  ł: "l",
  ń: "n",
  ś: "s",
  ź: "z",
  ż: "z",
  Ą: "A",
  Ć: "C",
  Ę: "E",
  Ł: "L",
  Ń: "N",
  Ś: "S",
  Ź: "Z",
  Ż: "Z",
  // latvian
  ā: "a",
  ē: "e",
  ģ: "g",
  ī: "i",
  ķ: "k",
  ļ: "l",
  ņ: "n",
  ū: "u",
  Ā: "A",
  Ē: "E",
  Ģ: "G",
  Ī: "I",
  Ķ: "K",
  Ļ: "L",
  Ņ: "N",
  Ū: "U",
  // lithuanian
  ė: "e",
  į: "i",
  ų: "u",
  Ė: "E",
  Į: "I",
  Ų: "U",
  // romanian
  ț: "t",
  Ț: "T",
  ţ: "t",
  Ţ: "T",
  ș: "s",
  Ș: "S",
  ă: "a",
  Ă: "A",
  // currency
  "€": "euro",
  "₢": "cruzeiro",
  "₣": "french franc",
  "£": "pound",
  "₤": "lira",
  "₥": "mill",
  "₦": "naira",
  "₧": "peseta",
  "₨": "rupee",
  "₩": "won",
  "₪": "new shequel",
  "₫": "dong",
  "₭": "kip",
  "₮": "tugrik",
  "₯": "drachma",
  "₰": "penny",
  "₱": "peso",
  "₲": "guarani",
  "₳": "austral",
  "₴": "hryvnia",
  "₵": "cedi",
  "¢": "cent",
  "¥": "yen",
  元: "yuan",
  円: "yen",
  "﷼": "rial",
  "₠": "ecu",
  "¤": "currency",
  "฿": "baht",
  $: "dollar",
  "₹": "indian rupee",
  // symbols
  "©": "(c)",
  œ: "oe",
  Œ: "OE",
  "∑": "sum",
  "®": "(r)",
  "†": "+",
  "“": '"',
  "”": '"',
  "‘": "'",
  "’": "'",
  "∂": "d",
  ƒ: "f",
  "™": "tm",
  "℠": "sm",
  "…": "...",
  "˚": "o",
  º: "o",
  ª: "a",
  "•": "*",
  "∆": "delta",
  "∞": "infinity",
  "♥": "love",
  "&": "and",
  "|": "or",
  "<": "less",
  ">": "greater",
  "=": "equals",
};

const multicharmap: Record<string, string> = {
  "<3": "love",
  "&&": "and",
  "||": "or",
  "w/": "with",
};

interface SlugifyOptions {
  replacement: string;
  remove: string | RegExp;
  charmap: Record<string, string>;
  multicharmap: Record<string, string>;
}

const pretty: SlugifyOptions = {
  replacement: "-",
  remove: /[.]/g,
  charmap,
  multicharmap,
};

export function slugify(rawString: string): string {
  const string = rawString.toString();
  const opts = pretty;
  const lengths: number[] = [];
  Object.keys(opts.multicharmap).forEach((key) => {
    const len = key.length;
    if (!lengths.includes(len)) {
      lengths.push(len);
    }
  });
  let result = "";
  for (let char, i = 0, l = string.length; i < l; i++) {
    char = string[i];
    if (
      !lengths.some((len) => {
        const str = string.substr(i, len);
        if (opts.multicharmap[str]) {
          i += len - 1;
          char = opts.multicharmap[str];
          return true;
        } else {
          return false;
        }
      })
    ) {
      if (opts.charmap[char]) {
        char = opts.charmap[char];
      }
    }
    char = char.replace(/[^\w\s\-._~]/g, ""); // allowed
    if (opts.remove) {
      // add flavour:
      char = char.replace(opts.remove, "");
    }
    result += char;
  }

  // trim leading/trailing spaces:
  result = result.replace(/^\s+|\s+$/g, "");
  // convert spaces:
  result = result.replace(/[-\s]+/g, opts.replacement);
  // remove trailing separator:
  return result.replace(opts.replacement + "$", "");
}
