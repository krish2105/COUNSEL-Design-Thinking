"use client";

/* THE CREW — the honest page.
 *
 * Two things a decision tool is normally careful not to say, said here first:
 * what each seat admits it gets wrong, and exactly what each one is able to do.
 * The capability table is the whole safety claim in one place, and it is easier
 * to trust because it is short.
 */

import { useEffect, useState } from "react";
import { RailEntry, type Seat as SeatId } from "@/components/Rail";
import { useLang } from "@/components/Providers";
import { Scrollable } from "@/components/Scrollable";
import { api, type Seat } from "@/lib/api";

export default function Crew() {
  const { t } = useLang();
  const [seats, setSeats] = useState<Seat[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.seats().then(setSeats).catch((e) => setError((e as Error).message));
  }, []);

  return (
    <div className="column">
      <h1 className="page-title">{t.crew.title}</h1>
      <p className="lede">{t.crew.lede}</p>
      {error ? <p className="erratum">{error}</p> : null}

      <div className="entries">
        {seats.map((s) => (
          <RailEntry key={s.id} seat={s.id as SeatId} mark={s.id.slice(0, 3)}>
            <h2 className="entry-title">{s.title}</h2>
            <p className="passage">{s.accountable_for}</p>

            <h3 className="sub">{t.crew.values}</h3>
            <ul className="blind-spots">
              {s.values.map((v) => (
                <li key={v}>{v}</li>
              ))}
            </ul>

            <h3 className="sub">{t.crew.blindSpots}</h3>
            <ul className="blind-spots">
              {s.blind_spots.map((b) => (
                <li key={b}>{b}</li>
              ))}
            </ul>

            <h3 className="sub">{t.crew.evidence}</h3>
            <ul className="blind-spots">
              {s.evidence_standards.map((e) => (
                <li key={e}>{e}</li>
              ))}
            </ul>

            <p className="citation">
              <span className="arm">{t.crew.tools}</span>
              {s.tools.map((tool) => (
                <span key={tool} className="span-ref">
                  {tool}
                </span>
              ))}
              <span className="arm">{t.crew.noSideEffects}</span>
            </p>
          </RailEntry>
        ))}
      </div>

      <section className="fenced">
        <h2 className="entry-title">{t.crew.capability}</h2>
        <p className="method">{t.crew.capabilityLede}</p>
        <Scrollable label={t.crew.capability}>
          <table className="ranking">
            <thead>
              <tr>
                <th>{t.crew.agent}</th>
                <th>{t.crew.tools}</th>
                <th>{t.crew.sideEffects}</th>
              </tr>
            </thead>
            <tbody>
              {seats.map((s) => (
                <tr key={s.id}>
                  <td>{s.title}</td>
                  <td>{s.tools.join(", ")}</td>
                  <td>{t.crew.none}</td>
                </tr>
              ))}
              <tr>
                <td>{t.crew.facilitator}</td>
                <td>start_round, close_round</td>
                <td>{t.crew.none}</td>
              </tr>
              <tr>
                <td>{t.crew.auditor}</td>
                <td>flag</td>
                <td>{t.crew.none}</td>
              </tr>
              <tr>
                <td>{t.crew.chair}</td>
                <td>ask, search</td>
                <td>{t.crew.none}</td>
              </tr>
            </tbody>
          </table>
        </Scrollable>
      </section>
    </div>
  );
}
