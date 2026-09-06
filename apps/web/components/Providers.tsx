"use client";

import { ThemeProvider } from "next-themes";
import { createContext, useContext, useEffect, useState } from "react";
import { DICT, DIR, type Dict, type Lang } from "@/lib/i18n";

const LangContext = createContext<{ lang: Lang; setLang: (l: Lang) => void; t: Dict }>({
  lang: "en",
  setLang: () => {},
  t: DICT.en,
});

export const useLang = () => useContext(LangContext);

export function Providers({ children }: { children: React.ReactNode }) {
  const [lang, setLang] = useState<Lang>("en");

  /* Read once on mount rather than during render: the server has no
   * localStorage, and reading it during render would desynchronise hydration. */
  useEffect(() => {
    const saved = window.localStorage.getItem("counsel-lang") as Lang | null;
    if (saved && saved in DICT) setLang(saved);
  }, []);

  useEffect(() => {
    document.documentElement.lang = lang;
    document.documentElement.dir = DIR[lang];
    window.localStorage.setItem("counsel-lang", lang);
  }, [lang]);

  return (
    <ThemeProvider attribute="data-theme" defaultTheme="dark" enableSystem>
      <LangContext.Provider value={{ lang, setLang, t: DICT[lang] }}>{children}</LangContext.Provider>
    </ThemeProvider>
  );
}
