import { afterEach, describe, expect, it } from "vitest";

import i18n from "./index";
import pt from "../../locales/pt-PT/common.json";
import en from "../../locales/en/common.json";
import fr from "../../locales/fr/common.json";
import es from "../../locales/es/common.json";

type Catalog = { [key: string]: string | Catalog };

function flatten(catalog: Catalog, prefix = ""): Record<string, string> {
  return Object.fromEntries(Object.entries(catalog).flatMap(([key, value]) => {
    const path = prefix ? `${prefix}.${key}` : key;
    return typeof value === "string" ? [[path, value]] : Object.entries(flatten(value, path));
  }));
}

const reference = flatten(pt);
const placeholders = (value: string) => value.match(/{{.*?}}/g)?.sort() ?? [];

afterEach(async () => { await i18n.changeLanguage("pt-PT"); });

describe.each(Object.entries({ en, fr, es }))("%s catalog", (locale, catalog) => {
  it("covers every Portuguese key and preserves interpolation variables", () => {
    const translated = flatten(catalog);
    for (const [key, value] of Object.entries(reference)) {
      expect(translated[key], key).toBeTruthy();
      expect(placeholders(translated[key]), key).toEqual(placeholders(value));
    }
    for (const key of Object.keys(translated)) {
      expect(reference[key] ?? reference[key.replace(/_many$/, "_other")], key).toBeDefined();
    }
  });

  it("has a local translation for every plural category used by the language", async () => {
    await i18n.changeLanguage(locale);
    for (const key of Object.keys(reference).filter((key) => key.endsWith("_other"))) {
      for (const count of [0, 1, 2, 1_000_000]) {
        const suffix = new Intl.PluralRules(locale).select(count);
        const pluralKey = key.replace(/_other$/, `_${suffix}`);
        expect(i18n.getResource(locale, "common", pluralKey), pluralKey).toBeTruthy();
        expect(i18n.t(key.replace(/_other$/, ""), { count, vehicle: "Car" })).not.toContain("{{");
      }
    }
  });
});

it.each([
  ["en", "Garage", "Have a good trip, Ana"],
  ["fr", "Garage", "Bonne route, Ana"],
  ["es", "Garaje", "Buen viaje, Ana"],
])("switches to %s and updates the document language", async (locale, garage, greeting) => {
  await i18n.changeLanguage(locale);
  expect(i18n.t("nav.garage")).toBe(garage);
  expect(i18n.t("dashboard.greeting", { name: "Ana" })).toBe(greeting);
  expect(document.documentElement.lang).toBe(locale);
});
