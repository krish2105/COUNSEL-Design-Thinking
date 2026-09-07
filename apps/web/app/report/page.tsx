"use client";

/* THE REPORT — everything assembled, and an export the reader performs.
 *
 * COUNSEL never sends this anywhere. There is no share button, no email field,
 * no webhook: the memo is rendered for a person to read, copy and do what they
 * like with. That is not an unbuilt feature — the project's promise is that no
 * agent can act on the world, and an export the software performs would be the
 * first exception.
 *
 * Printing is handled by a print stylesheet rather than a generated file, so
 * what comes out of the printer is the page the reader just checked.
 */

import { useCallback, useEffect, useState } from "react";
import { useLang } from "@/components/Providers";
import { Scrollable } from "@/components/Scrollable";
import {
  api,
  streamMemo,
  type Calibration,
  type MemoResult,
  type SessionState,
} from "@/lib/api";
import { currentSession } from "@/lib/session";

export default function Report() {
  const { t } = useLang();
  const [session, setSession] = useState<SessionState | null>(null);
  const [memo, setMemo] = useState<MemoResult | null>(null);
  const [calibration, setCalibration] = useState<Calibration | null>(null);
  const [verified, setVerified] = useState<boolean | null>(null);
  const [copied, setCopied] = useState(false);
  const [busy, setBusy] = useState(false);
  const [drafted, setDrafted] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const id = typeof window !== "undefined" ? currentSession() : null;

  useEffect(() => {
    if (!id) return;
    void (async () => {
      try {
        const [s, v, c] = await Promise.all([
          api.session(id),
          api.verify(id),
          api.calibration(),
        ]);
        setSession(s);
        setVerified(v.intact);
        setCalibration(c);
      } catch (e) {
        setError((e as Error).message);
      }
    })();
  }, [id]);

  /* Streamed, not awaited as one response. Assembling a memo is two model
   * phases — drafting against the corpus, then asking all five seats to
   * dissent — and measured at ~41s it returns 500 at exactly 30s through the
   * Next rewrite. The recommendation appears as soon as it is drafted, so the
   * wait shows its work instead of spinning. */
  const build = useCallback(async () => {
    if (!id) return;
    setBusy(true);
    setError(null);
    setDrafted(null);
    try {
      await streamMemo(id, (frame) => {
        if (frame.kind === "drafted") setDrafted(frame.recommendation);
        else if (frame.kind === "done") setMemo(frame);
      });
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }, [id]);

  async function copy() {
    if (!memo) return;
    try {
      await navigator.clipboard.writeText(memo.markdown);
      setCopied(true);
      setTimeout(() => setCopied(false), 2500);
    } catch {
      setError(t.report.copyFailed);
    }
  }

  if (!id) {
    return (
      <div className="column">
        <h1 className="page-title">{t.report.title}</h1>
        <p className="erratum">{t.decide.noSession}</p>
      </div>
    );
  }

  return (
    <div className="column">
      <h1 className="page-title">{t.report.title}</h1>
      <p className="lede">{t.report.lede}</p>

      {session ? (
        <dl className="meta">
          <div>
            <dt>{t.report.question}</dt>
            <dd>{session.question}</dd>
          </div>
          <div>
            <dt>{t.report.rounds}</dt>
            <dd>{session.round_no}</dd>
          </div>
          <div>
            <dt>{t.report.record}</dt>
            <dd>{verified === null ? "-" : verified ? t.report.sealed : t.report.broken}</dd>
          </div>
        </dl>
      ) : null}

      <div className="scanner-actions">
        <button type="button" onClick={() => void build()} disabled={busy}>
          {busy ? `${t.report.building}...` : t.report.build}
        </button>
        {memo ? (
          <>
            <button type="button" className="ghost" onClick={() => void copy()}>
              {copied ? t.report.copied : t.report.copy}
            </button>
            <button type="button" className="ghost" onClick={() => window.print()}>
              {t.report.print}
            </button>
          </>
        ) : null}
      </div>

      <p className="method">{t.report.exportNote}</p>
      {busy && drafted ? <p className="tag">{drafted}</p> : null}
      {error ? <p className="erratum">{error}</p> : null}

      {memo ? (
        <section className="fenced">
          <p className="tag">
            {memo.n_cited} {t.decide.cited} · {memo.n_uncited} {t.decide.uncited}
            {memo.unanimous_dissent ? ` · ${t.report.unanimous}` : ""}
          </p>
          <pre className="memo">{memo.markdown}</pre>
        </section>
      ) : null}

      {calibration ? (
        <section className="fenced">
          <h2 className="entry-title">{t.ledger.calibration}</h2>
          <p className="method">{calibration.note}</p>
          {calibration.scored.length === 0 ? (
            <p className="empty">
              {t.report.noCalibration.replace("{n}", String(calibration.minimum_outcomes))}
            </p>
          ) : (
            <Scrollable label={t.ledger.calibration}>
              <table className="ranking">
                <thead>
                  <tr>
                    <th>{t.crew.agent}</th>
                    <th>{t.ledger.brier}</th>
                    <th>{t.ledger.outcomes}</th>
                  </tr>
                </thead>
                <tbody>
                  {calibration.scored.map((b) => (
                    <tr key={b.seat}>
                      <td>{b.seat}</td>
                      <td className="num">{b.score.toFixed(3)}</td>
                      <td className="num">{b.n_outcomes}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </Scrollable>
          )}
        </section>
      ) : null}
    </div>
  );
}
