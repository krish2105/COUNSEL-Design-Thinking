"use client";

/* THE BOARD — framings and ideas, by seat.
 *
 * Ideate runs under a no-critique rule, so an idea here is shown with whose it
 * is and what it builds on, and never with a score. Ranking ideas on the board
 * would collapse the divergence the stage exists to protect.
 */

import { useCallback, useEffect, useState } from "react";
import { RailEntry, type Seat as SeatId } from "@/components/Rail";
import { useLang } from "@/components/Providers";
import {
  api,
  streamFramings,
  streamIdeas,
  type Framing,
  type Idea,
} from "@/lib/api";
import { currentSession } from "@/lib/session";

export default function Board() {
  const { t } = useLang();
  const [framings, setFramings] = useState<Record<string, Framing>>({});
  const [ideas, setIdeas] = useState<Record<string, Idea>>({});
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const id = typeof window !== "undefined" ? currentSession() : null;

  const load = useCallback(async () => {
    if (!id) return;
    try {
      const a = await api.artefacts(id);
      setFramings((a.artefacts.framing ?? {}) as Record<string, Framing>);
      setIdeas((a.artefacts.idea ?? {}) as Record<string, Idea>);
    } catch (e) {
      setError((e as Error).message);
    }
  }, [id]);

  useEffect(() => {
    void load();
  }, [load]);

  /* Streamed, so each seat appears as it answers.
   *
   * Five seats is ~21.7s for framings and ~19.4s for ideas on qwen3:8b — under
   * the 30-second ceiling every gateway imposes, but only because the model is
   * fast. A larger model or a slower host puts a synchronous response over it,
   * and the failure is the one the Report tab already demonstrated: 500 at
   * exactly 30s from the proxy while the endpoint completes fine.
   *
   * Frames arrive in completion order, which is the point — the room visibly
   * fills. The load() at the end re-reads the stored artefact, which is written
   * in seating order, so the settled view is stable regardless of who was
   * quickest. */
  async function run(kind: "framings" | "ideas") {
    if (!id) return;
    setBusy(kind);
    setError(null);
    try {
      if (kind === "framings") {
        setFramings({});
        await streamFramings(id, (frame) => {
          if (frame.kind !== "framing") return;
          const { kind: _kind, seat, ...framing } = frame;
          setFramings((prev) => ({ ...prev, [seat]: framing as Framing }));
        });
      } else {
        setIdeas({});
        await streamIdeas(id, (frame) => {
          if (frame.kind !== "idea") return;
          const { kind: _kind, seat, ...idea } = frame;
          setIdeas((prev) => ({ ...prev, [seat]: idea as Idea }));
        });
      }
      await load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(null);
    }
  }

  if (!id) {
    return (
      <div className="column">
        <h1 className="page-title">{t.board.title}</h1>
        <p className="erratum">{t.decide.noSession}</p>
      </div>
    );
  }

  return (
    <div className="column">
      <h1 className="page-title">{t.board.title}</h1>
      <p className="lede">{t.board.lede}</p>

      <div className="scanner-actions">
        <button type="button" onClick={() => void run("framings")} disabled={busy !== null}>
          {busy === "framings" ? `${t.board.working}...` : t.board.runFramings}
        </button>
        <button
          type="button"
          className="ghost"
          onClick={() => void run("ideas")}
          disabled={busy !== null}
        >
          {busy === "ideas" ? `${t.board.working}...` : t.board.runIdeas}
        </button>
      </div>

      {error ? <p className="erratum">{error}</p> : null}

      {Object.keys(framings).length > 0 ? (
        <section className="fenced">
          <h2 className="entry-title">{t.board.framings}</h2>
          <p className="method">{t.board.framingsLede}</p>
          <div className="entries">
            {Object.entries(framings).map(([seat, f]) => (
              <RailEntry key={seat} seat={seat as SeatId} mark={seat.slice(0, 3)}>
                <h3 className="entry-title">{f.hmw}</h3>
                <p className="passage">{f.why_it_matters}</p>
                <p className="citation">
                  <span className="arm">
                    {t.board.whose} {f.whose_problem}
                  </span>
                </p>
              </RailEntry>
            ))}
          </div>
        </section>
      ) : null}

      {/* Say what the state IS. An empty Board rendered nothing at all below the
          two buttons, which on a wide screen is a page-height of blank — it reads
          as broken rather than as "the room has not been asked yet". Every other
          surface here declares its own emptiness; this one did not. */}
      {!error &&
      !busy &&
      Object.keys(framings).length === 0 &&
      Object.keys(ideas).length === 0 ? (
        <p className="method">{t.board.empty}</p>
      ) : null}

      {Object.keys(ideas).length > 0 ? (
        <section className="fenced">
          <h2 className="entry-title">{t.board.ideas}</h2>
          <p className="method">{t.board.ideasLede}</p>
          <div className="entries">
            {Object.entries(ideas).map(([seat, idea]) => (
              <RailEntry
                key={seat}
                seat={seat as SeatId}
                mark={seat.slice(0, 3)}
                note={idea.builds_on ? `${t.board.buildsOn} ${idea.builds_on}` : undefined}
              >
                <h3 className="entry-title">{idea.title}</h3>
                <p className="passage">{idea.sketch}</p>
              </RailEntry>
            ))}
          </div>
        </section>
      ) : null}
    </div>
  );
}
