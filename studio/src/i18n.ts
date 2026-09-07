// SPDX-License-Identifier: Apache-2.0

import { enUS, type TranslationKey } from "./locales/en-US";
import { zhTW } from "./locales/zh-TW";

export type Locale = "en-US" | "zh-TW";
type Parameters = Record<string, string | number>;

export const resources: Record<Locale, Record<TranslationKey, string>> = {
  "en-US": enUS,
  "zh-TW": zhTW,
};

let activeLocale: Locale = "en-US";

function placeholders(value: string): string[] {
  return Array.from(
    value.matchAll(/\{\{([a-z][a-z0-9_]*)\}\}/g),
    (match) => match[1],
  ).sort();
}

export function validateResources(): void {
  const expected = Object.keys(enUS).sort();
  for (const locale of ["en-US", "zh-TW"] as const) {
    const dictionary = resources[locale];
    const actual = Object.keys(dictionary).sort();
    if (JSON.stringify(actual) !== JSON.stringify(expected)) {
      throw new Error("translation_key_mismatch");
    }
    for (const key of expected as TranslationKey[]) {
      if (
        typeof dictionary[key] !== "string" ||
        dictionary[key].trim() === ""
      ) {
        throw new Error("translation_value_invalid");
      }
      if (
        JSON.stringify(placeholders(dictionary[key])) !==
        JSON.stringify(placeholders(enUS[key]))
      ) {
        throw new Error("translation_placeholder_mismatch");
      }
    }
  }
}

validateResources();

export function resolveLocale(value: unknown): Locale {
  return value === "zh-TW" || value === "en-US" ? value : "en-US";
}

export function initialLocale(): Locale {
  try {
    const stored = window.localStorage.getItem("dc.locale");
    if (stored) return resolveLocale(stored);
    return resolveLocale(window.navigator.language);
  } catch {
    return "en-US";
  }
}

export function setLocale(locale: Locale): void {
  activeLocale = resolveLocale(locale);
  try {
    window.localStorage.setItem("dc.locale", activeLocale);
  } catch {
    // Preference persistence is optional presentation state, never authority.
  }
}

export function t(key: TranslationKey, parameters: Parameters = {}): string {
  const template = resources[activeLocale][key];
  const required = placeholders(template);
  const supplied = Object.keys(parameters).sort();
  if (JSON.stringify(required) !== JSON.stringify(supplied)) {
    throw new Error("translation_parameters_invalid");
  }
  return template.replace(/\{\{([a-z][a-z0-9_]*)\}\}/g, (_, name: string) =>
    String(parameters[name]),
  );
}
