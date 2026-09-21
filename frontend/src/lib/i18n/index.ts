import i18n from "i18next";
import { initReactI18next } from "react-i18next";

import es from "../../locales/es/common.json";
import fr from "../../locales/fr/common.json";
import en from "../../locales/en/common.json";
import ptPT from "../../locales/pt-PT/common.json";

// The session restores the language saved in the user's profile.
i18n.on("languageChanged", (language) => {
  document.documentElement.lang = language;
});

void i18n.use(initReactI18next).init({
  resources: {
    "pt-PT": { common: ptPT },
    en: { common: en },
    fr: { common: fr },
    es: { common: es },
  },
  lng: "pt-PT",
  supportedLngs: ["pt-PT", "en", "fr", "es"],
  fallbackLng: "pt-PT",
  defaultNS: "common",
  interpolation: { escapeValue: false },
});

export default i18n;
