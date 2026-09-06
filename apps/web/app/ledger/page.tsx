"use client";

/* THE LEDGER.
 *
 * The one screen that can turn "the agents' expertise is prompt-defined" from
 * an admission into a measurement — and the one most tempting to overclaim on.
 *
 * So it refuses to draw a score for a seat below the minimum, and says how many
 * more outcomes that seat needs instead. A calibration chart built on two
 * decisions is a chart of noise, and it would flatter whoever ran the fewest
 * sessions. The 0.25 line is named, because always saying "50%" scores exactly
 * that, and a seat above it is worse than a coin that admits it does not know.
 */

import { useCallback, useEffect, useState } from "react";
import { RailEntry, type Seat as SeatId } from "@/components/Rail";
import { useLang } from "@/components/Providers";
import { api, type Calibration } from "@/lib/api";
import { currentSession } from "@/lib/session";

export default function Ledger() {
  const { t } = useLang();
  const [data, setData] = useState<Calibration | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [chosen, setChosen] = useState("");
  const [actual, setActual] = useState("");
  const [notes, setNotes] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      setData(await api.calibration());
    } catch (e) {
      setError((e as Error).message);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function record(e: React.FormEvent) {
    e.preventDefault();
    const sessionId = currentSession();
    if (!sessionId || !chosen.trim() || !actual.trim()) return;
    setBusy(true);
    setError(null);
    try {
      await api.outcome(sessionId, chosen, actual, notes);
      setChosen("");
      setActual("");
      setNotes("");
      await load();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="column">
      <h1 className="page-title">{t.ledger.title}</h1>
      <p className="lede">{t.ledger.lede}</p>

      <form className="scanner" onSubmit={record}>
        <h2 className="entry-title">{t.ledger.record}</h2>
        <p className="lede">{t.ledger.recordLede}</p>
        <div className="askbar">
          <input
            value={chosen}
            onChange={(e) => setChosen(e.target.value)}
            placeholder={t.ledger.chosen}
            aria-label={t.ledger.chosen}
          />
          <input
            value={actual}
            onChange={(e) => setActual(e.target.value)}
            placeholder={t.ledger.actual}
            aria-label={t.ledger.actual}
          />
        </div>
        <textarea
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          rows={3}
          placeholder={t.ledger.notes}
          aria-label={t.ledger.notes}
        />
        <div className="scanner-actions">
          <button type="submit" disabled={busy || !chosen.trim() || !actual.trim()}>
            {t.ledger.save}
          </button>
        </div>
      </form>

      {error ? <p className="erratum">{error}</p> : null}

      {data ? (
        <>
          <section className="fenced">
            <h2 className="entry-title">{t.ledger.calibration}</h2>
            <p className="method">{data.note}</p>

            {data.scored.length > 0 ? (
              <div className="entries">
                {data.scored.map((b) => (
                  <RailEntry
                    key={b.seat}
                    seat={b.seat as SeatId}
                    mark={b.seat.slice(0, 3)}
                    note={b.score <= data.coin_flip_baseline ? undefined : t.ledger.worseThanCoin}
                  >
                    <p className="passage">{b.reading}</p>
                    <p className="citation">
                      <span className="span-ref">
                        {t.ledger.brier} {b.score.toFixed(3)}
                      </span>
                      <span className="span-ref">
                        {b.n_outcomes} {t.ledger.outcomes}
                      </span>
                      <span className="arm">
                        {t.ledger.hitRate} {(b.hit_rate * 100).toFixed(0)}%
                      </span>
                    </p>
                  </RailEntry>
                ))}
              </div>
            ) : null}

            {data.pending.length > 0 ? (
              <div className="entries">
                {data.pending.map((p) => (
                  <RailEntry
                    key={p.seat}
                    seat={p.seat as SeatId}
                    mark={p.seat.slice(0, 3)}
                    note={t.ledger.pending}
                  >
                    <p className="passage">
                      {t.ledger.needsMore.replace("{n}", String(p.needs))}{" "}
                      <span className="span-ref">
                        {p.n_outcomes}/{data.minimum_outcomes}
                      </span>
                    </p>
                  </RailEntry>
                ))}
              </div>
            ) : null}
          </section>

          <section className="fenced">
            <h2 className="entry-title">{t.ledger.outcomesTitle}</h2>
            {data.outcomes.length === 0 ? (
              <p className="empty">{t.ledger.noOutcomes}</p>
            ) : (
              <div className="entries">
                {data.outcomes.map((o, i) => (
                  <RailEntry
                    key={o.session_id}
                    mark={String(i + 1).padStart(2, "0")}
                    note={o.chosen === o.actual ? t.ledger.right : t.ledger.wrong}
                  >
                    <h3 className="entry-title">{o.question}</h3>
                    <p className="passage">{o.notes || t.ledger.noNotes}</p>
                    <p className="citation">
                      <span className="arm">
                        {t.ledger.chose} {o.chosen}
                      </span>
                      <span className="arm">
                        {t.ledger.wasRight} {o.actual}
                      </span>
                      <span className="span-ref">{o.recorded_at}</span>
                    </p>
                  </RailEntry>
                ))}
              </div>
            )}
          </section>
        </>
      ) : null}
    </div>
  );
}
