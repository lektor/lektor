import ca from "../../../translations/ca.json";
import de from "../../../translations/de.json";
import en from "../../../translations/en.json";
import es from "../../../translations/es.json";
import fr from "../../../translations/fr.json";
import it from "../../../translations/it.json";
import ja from "../../../translations/ja.json";
import ko from "../../../translations/ko.json";
import nl from "../../../translations/nl.json";
import pl from "../../../translations/pl.json";
import pt from "../../../translations/pt.json";
import ru from "../../../translations/ru.json";
import zh from "../../../translations/zh.json";

type LektorTranslations = typeof en;
export type TranslationEntry = keyof LektorTranslations;

export const translations: Record<string, Partial<LektorTranslations>> = {
  ca,
  de,
  en,
  es,
  fr,
  it,
  ja,
  ko,
  nl,
  pl,
  pt,
  ru,
  zh,
};

let currentLanguage = "en";
let currentTranslations = translations[currentLanguage] ?? {};

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
export function trans(key: TranslationEntry): string {
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
export function trans_format(
  key: TranslationEntry,
  replacement: string
): string {
  const translation = trans(key);
  return translation.replace("%s", replacement);
}
