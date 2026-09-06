"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTheme } from "next-themes";
import { useEffect, useState } from "react";
import { LANGS, LANG_LABEL, type Lang } from "@/lib/i18n";
import { useLang } from "./Providers";

export function Masthead() {
  const { lang, setLang, t } = useLang();
  const { resolvedTheme, setTheme } = useTheme();
  const path = usePathname();
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  const tabs = [
    { href: "/room", label: t.nav.room },
    { href: "/decide", label: t.nav.decide },
    { href: "/ledger", label: t.nav.ledger },
    { href: "/", label: t.nav.documents },
    { href: "/ask", label: t.nav.ask },
    { href: "/security", label: t.nav.security },
  ];

  return (
    <header className="masthead">
      <Link href="/" className="brand">
        <span className="brand-mark">{t.brand}</span>
        <span className="brand-tagline">{t.tagline}</span>
      </Link>

      <nav aria-label={t.brand}>
        {tabs.map((tab) => (
          <Link
            key={tab.href}
            href={tab.href}
            className="tab"
            aria-current={path === tab.href ? "page" : undefined}
          >
            {tab.label}
          </Link>
        ))}
      </nav>

      <div className="controls">
        <div className="langs" role="group" aria-label="Language">
          {LANGS.map((code: Lang) => (
            <button
              key={code}
              type="button"
              onClick={() => setLang(code)}
              aria-pressed={lang === code}
              className="lang"
            >
              {LANG_LABEL[code]}
            </button>
          ))}
        </div>
        <button
          type="button"
          className="theme"
          onClick={() => setTheme(resolvedTheme === "dark" ? "light" : "dark")}
        >
          {mounted ? (resolvedTheme === "dark" ? t.theme.light : t.theme.dark) : " "}
        </button>
      </div>
    </header>
  );
}
