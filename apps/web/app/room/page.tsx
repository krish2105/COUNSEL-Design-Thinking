"use client";

/* THE ROOM.
 *
 * Where the margin rail finally does the job it was built for: each seat's turn
 * hangs against the rule in that seat's colour, and an Auditor flag sits in the
 * margin beside the words that caused it — marginalia, not a toast.
 *
 * Two kinds of frame arrive over the same stream and they are shown
 * differently on purpose. A `speaking` frame is what a seat said the moment it
 * finished: unsigned, in completion order, and explicitly labelled. A `turn`
 * frame is the sealed record, in seating order. A transcript you can trust and
 * a preview you cannot must never look alike.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { Chamber, type ChamberData } from "@/components/chamber/Chamber";
import { RailEntry, type Seat as SeatId } from "@/components/Rail";
import { useLang } from "@/components/Providers";
import { api, streamRound, type Frame, type Seat, type SessionState } from "@/lib/api";
import { currentSession, setCurrentSession } from "@/lib/session";
import { assignVoices, loadVoices, speak, speechAvailable, stopSpeaking, type VoiceMap } from "@/lib/voice";

const STAGES = ["Empathise", "Define", "Ideate", "Prototype", "Test", "Decide", "Learn"];
const DEMO = "Should RAQIB pilot in a Dubai hypermarket or a Greenlam plant first?";

type Spoken = {
  seat: string;
  text: string;
  signed: boolean;
  sig?: string;
  model?: string;
  turnId?: string;
};
type Flag = { turn_id: string; rule: string; severity: string; excerpt: string; why: string };

export default function Room() {
  const { t } = useLang();
  const [seats, setSeats] = useState<Seat[]>([]);
  const [question, setQuestion] = useState(DEMO);
  const [stage, setStage] = useState("Decide");
  const [session, setSession] = useState<SessionState | null>(null);
  const [spoken, setSpoken] = useState<Record<string, Spoken>>({});
  const [flags, setFlags] = useState<Flag[]>([]);
  const [status, setStatus] = useState("");
  const [busy, setBusy] = useState(false);
  const [chair, setChair] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [chamber, setChamber] = useState<ChamberData | null>(null);
  const [voices, setVoices] = useState<VoiceMap>({});
  /* Off by default: a page that starts talking when you open it is a page
   * people close. */
  const [voiceOn, setVoiceOn] = useState(false);
  const abort = useRef<AbortController | null>(null);

  useEffect(() => {
    api.seats().then(setSeats).catch((e) => setError((e as Error).message));

    /* Restore the session the other tabs are working on. Without this, walking
     * to the Memo and back would drop you at an empty form with the debate you
     * just ran still sitting in the database, unreachable. */
    const existing = currentSession();
    if (existing) {
      void (async () => {
        try {
          const [state, room] = await Promise.all([
            api.session(existing),
            api.chamber(existing),
          ]);
          setSession(state);
          setChamber(room);
        } catch {
          // The session is gone (a restart cleared the database, say). Leaving
          // the form empty is the right answer; a stale id is not an error the
          // reader needs to see.
        }
      })();
    }

    if (speechAvailable()) {
      void loadVoices().then((v) => setVoices(assignVoices(v)));
    }

    return () => {
      abort.current?.abort();
      stopSpeaking();
    };
  }, []);

  const open = useCallback(async () => {
    setBusy(true);
    setError(null);
    setSpoken({});
    setFlags([]);
    try {
      const opened = await api.openSession(question, stage);
      setSession(opened);
      setCurrentSession(opened.session_id);
      setChamber(await api.chamber(opened.session_id));
      setStatus(t.room.opened);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }, [question, stage, t.room.opened]);

  const runRound = useCallback(async () => {
    if (!session) return;
    setBusy(true);
    setError(null);
    setSpoken({});
    setFlags([]);
    abort.current = new AbortController();
    try {
      await streamRound(
        session.session_id,
        (f: Frame) => {
          if (f.kind === "round_open") {
            setStatus(`${t.room.round} ${f.round_no} — ${f.stage}`);
          } else if (f.kind === "speaking") {
            setSpoken((p) => ({ ...p, [f.seat]: { seat: f.seat, text: f.text, signed: false } }));
          } else if (f.kind === "turn") {
            if (voiceOn) speak(f.speaker as never, f.text, voices);
            setSpoken((p) => ({
              ...p,
              [f.speaker]: {
                seat: f.speaker,
                text: f.text,
                signed: true,
                sig: f.sig,
                model: f.model,
                turnId: f.turn_id,
              },
            }));
          } else if (f.kind === "flag") {
            setFlags((p) => [...p, f]);
          } else if (f.kind === "done") {
            setStatus(
              f.chain_intact
                ? `${t.room.sealed} · ${f.n_flags} ${t.room.flags}`
                : t.room.broken,
            );
            api.session(session.session_id).then(setSession).catch(() => undefined);
            api.chamber(session.session_id).then(setChamber).catch(() => undefined);
          }
        },
        abort.current.signal,
      );
    } catch (e) {
      if ((e as Error).name !== "AbortError") setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }, [session, t.room, voiceOn, voices]);

  async function interject(e: React.FormEvent) {
    e.preventDefault();
    if (!session || !chair.trim()) return;
    try {
      await api.interject(session.session_id, chair);
      setChair("");
      setStatus(t.room.chairHeard);
      setSession(await api.session(session.session_id));
      setChamber(await api.chamber(session.session_id));
    } catch (err) {
      setError((err as Error).message);
    }
  }

  /* Seating order, not arrival order: the record is ordered, so the reading of
   * it is too. Only seats that have spoken this round appear. */
  const ordered = seats.map((s) => spoken[s.id]).filter(Boolean) as Spoken[];

  return (
    <div
      className="column"
      /* The real voice assignment, exposed so a test can check the property
       * that makes the feature worth having: the CFO sounds like the CFO in
       * every session and every replay. A test that re-implemented the dealing
       * rule would only be testing itself. */
      data-voices={Object.entries(voices)
        .map(([seat, v]) => `${seat}:${v?.name ?? ""}`)
        .join(",")}
    >
      <h1 className="page-title">{t.room.title}</h1>
      <p className="lede">{t.room.lede}</p>

      {!session ? (
        <form
          className="askbar room-open"
          onSubmit={(e) => {
            e.preventDefault();
            void open();
          }}
        >
          <input
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            aria-label={t.room.question}
          />
          <select
            value={stage}
            onChange={(e) => setStage(e.target.value)}
            aria-label={t.room.stage}
          >
            {STAGES.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
          <button type="submit" disabled={busy}>
            {t.room.open}
          </button>
        </form>
      ) : (
        <div className="room-bar">
          <dl className="meta">
            <div>
              <dt>{t.room.stage}</dt>
              <dd>{session.stage}</dd>
            </div>
            <div>
              <dt>{t.room.round}</dt>
              <dd>{session.round_no}</dd>
            </div>
            <div>
              <dt>{t.room.record}</dt>
              <dd>{session.chain_intact ? t.room.sealed : t.room.broken}</dd>
            </div>
          </dl>
          <div className="scanner-actions">
            <button type="button" onClick={() => void runRound()} disabled={busy}>
              {busy ? `${t.room.arguing}...` : t.room.runRound}
            </button>
            {busy ? (
              <button type="button" className="ghost" onClick={() => abort.current?.abort()}>
                {t.room.stop}
              </button>
            ) : null}
            {speechAvailable() ? (
              <button
                type="button"
                className="ghost"
                aria-pressed={voiceOn}
                onClick={() => {
                  if (voiceOn) stopSpeaking();
                  setVoiceOn(!voiceOn);
                }}
              >
                {voiceOn ? t.room.voiceOff : t.room.voiceOn}
              </button>
            ) : null}
          </div>
          {status ? <p className="tag">{status}</p> : null}
        </div>
      )}

      {error ? <p className="erratum">{error}</p> : null}

      {chamber ? (
        <Chamber
          data={chamber}
          labels={{
            replay: t.room.replay,
            turn: t.room.turn,
            of: t.room.of,
            fallbackNote: t.room.fallbackNote,
            silent: t.room.silent,
            speaking: t.room.speakingNow,
          }}
        />
      ) : null}

      {ordered.length > 0 ? (
        <div className="entries">
          {ordered.map((turn) => {
            const seat = seats.find((s) => s.id === turn.seat);
            const mine = turn.turnId ? flags.filter((f) => f.turn_id === turn.turnId) : [];
            return (
              <RailEntry
                key={turn.seat}
                seat={turn.seat as SeatId}
                mark={turn.seat.slice(0, 3)}
                note={turn.signed ? undefined : t.room.unsigned}
              >
                <h2 className="entry-title">{seat?.title ?? turn.seat}</h2>
                <p className="passage">{turn.text}</p>
                <p className="citation">
                  {turn.signed ? (
                    <>
                      <span className="hash">{turn.sig}</span>
                      <span className="arm">{t.room.sealed}</span>
                      {turn.model ? <span className="arm">{turn.model}</span> : null}
                    </>
                  ) : (
                    <span className="arm">{t.room.unsignedNote}</span>
                  )}
                </p>
                {mine.map((f) => (
                  <p key={f.rule} className="erratum">
                    <strong>{f.rule}</strong> {f.why}
                  </p>
                ))}
              </RailEntry>
            );
          })}
        </div>
      ) : null}

      {session ? (
        <form className="scanner chair" onSubmit={interject}>
          <h2 className="entry-title">{t.room.chair}</h2>
          <p className="lede">{t.room.chairLede}</p>
          <textarea
            value={chair}
            onChange={(e) => setChair(e.target.value)}
            rows={3}
            aria-label={t.room.chair}
            placeholder={t.room.chairPlaceholder}
          />
          <div className="scanner-actions">
            <button type="submit" disabled={!chair.trim()}>
              {t.room.speak}
            </button>
          </div>
        </form>
      ) : null}

      {seats.length > 0 ? (
        <section className="fenced">
          <h2 className="entry-title">{t.room.blindSpots}</h2>
          <p className="lede">{t.room.blindSpotsLede}</p>
          <div className="entries">
            {seats.map((s) => (
              <RailEntry key={s.id} seat={s.id as SeatId} mark={s.id.slice(0, 3)}>
                <h3 className="entry-title">{s.title}</h3>
                <ul className="blind-spots">
                  {s.blind_spots.map((b) => (
                    <li key={b}>{b}</li>
                  ))}
                </ul>
              </RailEntry>
            ))}
          </div>
        </section>
      ) : null}
    </div>
  );
}
