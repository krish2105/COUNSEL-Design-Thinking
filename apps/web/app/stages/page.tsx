"use client";

/* THE STAGES — Empathise to Learn, and what binds at each.
 *
 * The rules are not printed as a reminder. Every one of them is either enforced
 * by a schema or flagged by the Auditor, and showing them beside what the room
 * produced is how a reader checks that the stage was actually observed rather
 * than merely named.
 */

import { useEffect, useState } from "react";
import { RailEntry } from "@/components/Rail";
import { useLang } from "@/components/Providers";
import { api } from "@/lib/api";
import { currentSession } from "@/lib/session";

const ORDER = ["Empathise", "Define", "Ideate", "Prototype", "Test", "Decide", "Learn"];
const PRODUCES: Record<string, string> = {
  Define: "framing",
  Ideate: "idea",
  Test: "score",
  Decide: "dissent",
};

export default function Stages() {
  const { t } = useLang();
  const [rules, setRules] = useState<Record<string, string[]>>({});
  const [produced, setProduced] = useState<Record<string, number>>({});
  const [stage, setStage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const id = currentSession();
    if (!id) return;
    void (async () => {
      try {
        const [a, s] = await Promise.all([api.artefacts(id), api.session(id)]);
        setRules(a.stage_rules);
        setStage(s.stage);
        setProduced(
          Object.fromEntries(
            Object.entries(a.artefacts).map(([kind, payload]) => [
              kind,
              payload ? Object.keys(payload).length : 0,
            ]),
          ),
        );
      } catch (e) {
        setError((e as Error).message);
      }
    })();
  }, []);

  return (
    <div className="column">
      <h1 className="page-title">{t.stages.title}</h1>
      <p className="lede">{t.stages.lede}</p>
      {error ? <p className="erratum">{error}</p> : null}

      <div className="entries">
        {ORDER.map((name, i) => {
          const kind = PRODUCES[name];
          const count = kind ? (produced[kind] ?? 0) : 0;
          return (
            <RailEntry
              key={name}
              mark={String(i + 1).padStart(2, "0")}
              note={name === stage ? t.stages.here : undefined}
            >
              <h2 className="entry-title">{name}</h2>
              <ul className="blind-spots">
                {(rules[name] ?? []).map((r) => (
                  <li key={r}>{r}</li>
                ))}
              </ul>
              <p className="citation">
                <span className="arm">
                  {kind
                    ? count > 0
                      ? `${count} ${t.stages.produced}`
                      : t.stages.notYet
                    : t.stages.noArtefact}
                </span>
              </p>
            </RailEntry>
          );
        })}
      </div>
    </div>
  );
}
