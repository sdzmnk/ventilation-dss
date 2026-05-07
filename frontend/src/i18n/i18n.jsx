import { createContext, useContext, useEffect, useMemo, useState } from "react";
import uk from "./uk.js";
import en from "./en.js";

const dicts = { uk, en };
const I18nCtx = createContext(null);

export function I18nProvider({ children }) {
  const [lang, setLang] = useState(localStorage.getItem("vdss.lang") || "uk");

  useEffect(() => {
    localStorage.setItem("vdss.lang", lang);
    document.documentElement.lang = lang;
  }, [lang]);

  const value = useMemo(() => {
    const dict = dicts[lang] || uk;
    const t = (key, vars) => {
      let s = dict[key] ?? key;
      if (vars) {
        for (const [k, v] of Object.entries(vars)) {
          s = s.replaceAll(`{${k}}`, String(v));
        }
      }
      return s;
    };
    return { lang, setLang, t };
  }, [lang]);

  return <I18nCtx.Provider value={value}>{children}</I18nCtx.Provider>;
}

export function useI18n() {
  return useContext(I18nCtx);
}
