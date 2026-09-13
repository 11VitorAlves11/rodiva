import i18n from "i18next";
import { initReactI18next } from "react-i18next";

import en from "../../locales/en/common.json";
import ptPT from "../../locales/pt-PT/common.json";

// pt-PT is the product's default locale (RF-ADM-002/RF-ADM-003); English is the
// only other language shipped in v1. Per-user language choice is stored on the
// account (RF-AUT-009) once profile settings exist — until then this is fixed.
void i18n.use(initReactI18next).init({
  resources: {
    "pt-PT": { common: ptPT },
    en: { common: en },
  },
  lng: "pt-PT",
  fallbackLng: "pt-PT",
  defaultNS: "common",
  interpolation: { escapeValue: false },
});

export default i18n;
