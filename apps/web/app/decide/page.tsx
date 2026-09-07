"use client";

/* DECIDE.
 *
 * The arc from evidence to memo, on one page, in the order it actually
 * happens: name what the room may lean on, score the options, ask what would
 * flip it, then write the memo.
 *
 * Two things are shown that a decision tool is usually careful to hide. The
 * counterfactual says out loud that it is a sensitivity analysis and not a
 * re-run of the argument. And the memo reports how many of its own claims are
 * uncited, in the same line as how many are cited, because a memo that is 2/9
 * evidenced is a different document from one that is 9/9 and a reader deserves
 * to know which they are holding.
 */

import { useCallback, useEffect, useState } from "react";
import { RailEntry, type Seat as SeatId } from "@/components/Rail";
import { useLang } from "@/components/Providers";
import { Scrollable } from "@/components/Scrollable";
import {
  api,
  streamScores,
  type Counterfactual,
  type MemoResult,
  type Ranked,
  type ScoreFrame,
} from "@/lib/api";
import { currentSession } from "@/lib/session";

type Row = { evidence_id: string; summary: string; source: string };

const SUGGESTED: Row[] = [
  { evidence_id: "e1", summary: "footfall estimate for the hypermarket", source: "estate report" },
  { evidence_id: "e2", summary: "payback model for both options", source: "treasury" },
  { evidence_id: "e3", summary: "plant capacity and shift audit", source: "operations" },
];

export default function Decide() {
  const { t } = useLang();
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [evidence, setEvidence] = useState<Row[]>(SUGGESTED);
  const [options, setOptions] = useState("hypermarket, plant");
  const [ranked, setRanked] = useState<Ranked[] | null>(null);
  const [cf, setCf] = useState<Counterfactual | null>(null);
  const [memo, setMemo] = useState<MemoResult | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [progress, setProgress] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => setSessionId(currentSession()), []);

  const guard = useCallback(
    async (label: string, run: () => Promise<void>) => {
      setBusy(label);
      setError(null);
      try {
        await run();
      } catch (e) {
        setError((e as Error).message);
      } finally {
        setBusy(null);
      }
    },
    [],
  );

  /* Streamed, not because a progress bar is nice but because a ~100s
   * synchronous response dies at every gateway between here and the API — the
   * dev rewrite returns 500 at exactly 30 seconds. Frames keep it alive, and
   * the person waiting gets to watch the seats land. */
  const scoreOptions = () =>
    guard("score", async () => {
      if (!sessionId) return;
      setRanked(null);
      setCf(null);
      setProgress([]);
      await api.addEvidence(sessionId, evidence);
      await streamScores(
        sessionId,
        options.split(",").map((o) => o.trim()).filter(Boolean),
        (f: ScoreFrame) => {
          if (f.kind === "scored") {
            setProgress((p) => [...p, `${f.seat} scored ${f.option}`]);
          } else if (f.kind === "ranked") {
            setRanked(f.ranked);
          }
        },
      );
      setCf(await api.counterfactual(sessionId));
    });

  const writeMemo = () =>
    guard("memo", async () => {
      if (!sessionId) return;
      setMemo(await api.memo(sessionId));
    });

  if (!sessionId) {
    return (
      <div className="column">
        <h1 className="page-title">{t.decide.title}</h1>
        <p className="lede">{t.decide.lede}</p>
        <p className="erratum">{t.decide.noSession}</p>
      </div>
    );
  }

  return (
    <div className="column">
      <h1 className="page-title">{t.decide.title}</h1>
      <p className="lede">{t.decide.lede}</p>

      <section className="scanner">
        <h2 className="entry-title">{t.decide.evidence}</h2>
        <p className="lede">{t.decide.evidenceLede}</p>
        {evidence.map((row, i) => (
          <div className="evidence-row" key={row.evidence_id}>
            <input
              value={row.summary}
              aria-label={`${t.decide.evidence} ${row.evidence_id}`}
              onChange={(e) =>
                setEvidence((p) =>
                  p.map((r, j) => (i === j ? { ...r, summary: e.target.value } : r)),
                )
              }
            />
            <button
              type="button"
              className="ghost"
              onClick={() => setEvidence((p) => p.filter((_, j) => j !== i))}
            >
              {t.decide.remove}
            </button>
          </div>
        ))}
        <div className="scanner-actions">
          <button
            type="button"
            className="ghost"
            onClick={() =>
              setEvidence((p) => [
                ...p,
                { evidence_id: `e${p.length + 1}`, summary: "", source: "user" },
              ])
            }
          >
            {t.decide.addEvidence}
          </button>
        </div>
      </section>

      <section className="scanner">
        <h2 className="entry-title">{t.decide.options}</h2>
        <div className="askbar">
          <input
            value={options}
            onChange={(e) => setOptions(e.target.value)}
            aria-label={t.decide.options}
          />
          <button type="button" onClick={scoreOptions} disabled={busy !== null}>
            {busy === "score" ? `${t.decide.scoring}...` : t.decide.score}
          </button>
        </div>
      </section>

      {error ? <p className="erratum">{error}</p> : null}
      {busy === "score" && progress.length > 0 ? (
        <p className="tag">{progress[progress.length - 1]} · {progress.length}</p>
      ) : null}

      {ranked ? (
        <section className="fenced">
          <h2 className="entry-title">{t.decide.ranking}</h2>
          <Scrollable label={t.decide.ranking}>
            <table className="ranking">
              <thead>
                <tr>
                  <th>{t.decide.option}</th>
                  <th>{t.decide.total}</th>
                  <th>{t.decide.confidence}</th>
                  <th>{t.decide.seats}</th>
                </tr>
              </thead>
              <tbody>
                {ranked.map((r) => (
                  <tr key={r.option}>
                    <td>{r.option}</td>
                    <td className="num">{r.total}</td>
                    <td className="num">{r.mean_confidence.toFixed(2)}</td>
                    <td>{r.supporters.join(", ")}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Scrollable>
        </section>
      ) : null}

      {cf ? (
        <section className="fenced">
          <h2 className="entry-title">{t.decide.counterfactual}</h2>
          <p className="verdict">{cf.verdict}</p>
          <p className="method">{cf.method}</p>

          {cf.flips.length > 0 ? (
            <div className="entries">
              {cf.flips.map((f) => (
                <RailEntry key={f.evidence_id} mark={f.evidence_id} note={t.decide.flip}>
                  <p className="passage">
                    {t.decide.remove} <strong>{f.summary}</strong> {t.decide.andTheRoomPrefers}{" "}
                    <strong>{f.winner_after}</strong> {t.decide.insteadOf}{" "}
                    <strong>{f.winner_before}</strong>.
                  </p>
                  <p className="citation">
                    <span className="span-ref">
                      {f.margin_before.toFixed(0)} &rarr; {f.margin_after.toFixed(0)}
                    </span>
                    <span className="arm">{f.seats_affected.join(", ")}</span>
                  </p>
                </RailEntry>
              ))}
            </div>
          ) : null}

          <div className="entries">
            {cf.sensitivity.map((s) => (
              <RailEntry
                key={s.seat}
                seat={s.seat as SeatId}
                mark={s.seat.slice(0, 3)}
                note={s.ungrounded ? t.decide.ungrounded : undefined}
              >
                <p className="citation">
                  <span className="arm">
                    {s.ungrounded
                      ? t.decide.argueFromMandate
                      : `${t.decide.leaningOn} ${s.depends_on.join(", ")}`}
                  </span>
                </p>
              </RailEntry>
            ))}
          </div>
        </section>
      ) : null}

      {ranked ? (
        <section className="scanner">
          <div className="scanner-actions">
            <button type="button" onClick={writeMemo} disabled={busy !== null}>
              {busy === "memo" ? `${t.decide.writing}...` : t.decide.writeMemo}
            </button>
          </div>
        </section>
      ) : null}

      {memo ? (
        <section className="fenced">
          <h2 className="entry-title">{t.decide.memo}</h2>
          <p className="tag">
            {memo.n_cited} {t.decide.cited} · {memo.n_uncited} {t.decide.uncited}
            {memo.ungrounded ? ` · ${t.decide.ungroundedMemo}` : ""}
          </p>
          <pre className="memo">{memo.markdown}</pre>
        </section>
      ) : null}
    </div>
  );
}
