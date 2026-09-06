"use client";

import { useState } from "react";
import { RailEntry } from "@/components/Rail";
import { useLang } from "@/components/Providers";
import { api, type Hit } from "@/lib/api";

export default function Ask() {
  const { t } = useLang();
  const [q, setQ] = useState("");
  const [hits, setHits] = useState<Hit[] | null>(null);
  const [degraded, setDegraded] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run(e: React.FormEvent) {
    e.preventDefault();
    if (!q.trim()) return;
    setBusy(true);
    setError(null);
    try {
      const res = await api.retrieve(q, 8);
      setHits(res.hits);
      setDegraded(res.degraded);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  /* Which arm found this passage is worth showing, not hiding: it is the
   * difference between "these words appear here" and "this means the same
   * thing", and on a trilingual corpus only the second can cross a script. */
  function arms(hit: Hit) {
    if (hit.rank_bm25 !== null && hit.rank_vec !== null) return t.ask.both;
    return hit.rank_vec !== null ? t.ask.semantic : t.ask.lexical;
  }

  return (
    <div className="column">
      <h1 className="page-title">{t.ask.title}</h1>
      <p className="lede">{t.ask.lede}</p>

      <form className="askbar" onSubmit={run}>
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder={t.ask.placeholder}
          aria-label={t.ask.title}
        />
        <button type="submit" disabled={busy}>
          {busy ? `${t.ask.searching}…` : t.ask.submit}
        </button>
      </form>

      {error ? <p className="erratum">{error}</p> : null}
      {degraded.length > 0 ? (
        <p className="erratum">
          {t.ask.degraded} — {degraded.join(" · ")}
        </p>
      ) : null}

      {hits === null ? null : hits.length === 0 ? (
        <p className="empty">{t.ask.empty}</p>
      ) : (
        <div className="entries">
          {hits.map((hit, i) => (
            <RailEntry key={hit.chunk_id} mark={String(i + 1).padStart(2, "0")} note={hit.lang}>
              <p className="passage" lang={hit.lang} dir={hit.lang === "ar" ? "rtl" : "ltr"}>
                {hit.text}
              </p>
              <p className="citation">
                <span className="hash">{hit.doc_id.slice(0, 12)}</span>
                <span className="span-ref">
                  [{hit.start}, {hit.end})
                </span>
                <span className="arm">{arms(hit)}</span>
              </p>
            </RailEntry>
          ))}
        </div>
      )}
    </div>
  );
}
