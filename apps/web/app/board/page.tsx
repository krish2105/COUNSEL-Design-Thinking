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
import { api } from "@/lib/api";
import { currentSession } from "@/lib/session";

type Framing = { hmw: string; why_it_matters: string; whose_problem: string };
type Idea = { title: string; sketch: string; builds_on: string | null };

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

  async function run(kind: "framings" | "ideas") {
    if (!id) return;
    setBusy(kind);
    setError(null);
    try {
      if (kind === "framings") await api.framings(id);
      else await api.ideas(id);
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
