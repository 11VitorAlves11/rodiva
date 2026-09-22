import i18n from "i18next";
import { initReactI18next } from "react-i18next";

import es from "../../locales/es/common.json";
import fr from "../../locales/fr/common.json";
import en from "../../locales/en/common.json";
import ptPT from "../../locales/pt-PT/common.json";

/** The account stores "en"; the catalogue is British, and so are the dates and numbers
 * every `Intl` call derives from `i18n.language` — bare "en" would format them as
 * 9/18/2026 next to kilometres and euros. Map on the way in rather than at 70-odd
 * formatting call sites. */
const TAGS: Record<string, string> = { en: "en-GB" };

export function applyLocale(locale: string): Promise<unknown> {
  return i18n.changeLanguage(TAGS[locale] ?? locale);
}

// The session restores the language saved in the user's profile.
i18n.on("languageChanged", (language) => {
  document.documentElement.lang = language;
});

void i18n.use(initReactI18next).init({
  resources: {
    "pt-PT": { common: ptPT },
    "en-GB": { common: en },
    fr: { common: fr },
    es: { common: es },
  },
  lng: "pt-PT",
  supportedLngs: ["pt-PT", "en-GB", "fr", "es"],
  fallbackLng: "pt-PT",
  defaultNS: "common",
  interpolation: { escapeValue: false },
});

export default i18n;
