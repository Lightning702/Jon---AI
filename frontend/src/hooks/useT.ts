import { useEffect, useState } from "react";
import { de, Translations } from "../i18n/de";
import { en } from "../i18n/en";

let currentLang = localStorage.getItem("jon_lang") || "de";

export const getLang = () => currentLang;
export const setLang = (lang: string) => {
  currentLang = lang;
  localStorage.setItem("jon_lang", lang);
  window.dispatchEvent(new Event("jon_lang_change"));
};

export function useT() {
  const [lang, setLangState] = useState(currentLang);

  useEffect(() => {
    const handler = () => setLangState(currentLang);
    window.addEventListener("jon_lang_change", handler);
    return () => window.removeEventListener("jon_lang_change", handler);
  }, []);

  const t = (key: keyof Translations, params?: Record<string, string | number>) => {
    const dict = lang === "en" ? en : de;
    let str = dict[key] || de[key] || key;
    if (params) {
      for (const [k, v] of Object.entries(params)) {
        str = str.replace(`{${k}}`, String(v));
      }
    }
    return str;
  };

  return { t, lang, setLang };
}
