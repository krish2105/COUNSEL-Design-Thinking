"use client";

/* Picks a view of the table, and scrubs a debate through it.
 *
 * The 3D scene is lazy: it is the heaviest thing in the app and every other tab
 * works without it, so it is not in the bundle a reader downloads to look at a
 * memo. If WebGL is absent or the reader has asked for reduced motion, the SVG
 * renders instead — the same seats, the same edges, from the same numbers.
 *
 * The caption under the table is not decoration. A diagram looks like data, and
 * this one is a derivation: an edge means one seat named another, and nothing
 * about agreement or intensity. Saying so under the picture is the only place a
 * reader will actually read it.
 */

import dynamic from "next/dynamic";
import { useEffect, useMemo, useState } from "react";
import { SEATS, cssColourToHex, isWebGLAvailable, type Seat } from "@/lib/chamber";
import type { Variant } from "./scenes";
import { TableSVG, type ChamberEdge } from "./TableSVG";

const Table3D = dynamic(() => import("./Table3D").then((m) => m.Table3D), {
  ssr: false,
  loading: () => <div className="chamber-loading" />,
});

export type ChamberTurn = {
  turn_id: string;
  ordinal: number;
  round_no: number;
  stage: string;
  speaker: string;
  text: string;
  is_seat: boolean;
  sig: string;
};

export type ChamberData = {
  seats: { id: string; title: string; index: number }[];
  turns: ChamberTurn[];
  edges: ChamberEdge[];
  rounds: number[];
  chain_intact: boolean;
  shows: string;
};

/** Read the seat colours out of the stylesheet, so the table and the margin
 *  rail cannot drift apart — there is one definition, in tokens.css. */
function seatColours(): Record<string, string> {
  if (typeof window === "undefined") return {};
  const style = getComputedStyle(document.documentElement);
  return Object.fromEntries(
    SEATS.map((seat) => {
      const token = style.getPropertyValue(`--seat-${seat}`).trim();
      return [seat, cssColourToHex(token) ?? "#8890a8"];
    }),
  );
}

const VARIANTS: { id: Variant; label: string }[] = [
  { id: "obsidian", label: "Obsidian" },
  { id: "architect", label: "Model" },
  { id: "candlelit", label: "Candlelit" },
  { id: "orrery", label: "Orrery" },
];

export function Chamber({
  data,
  labels,
}: {
  data: ChamberData;
  labels: {
    replay: string;
    turn: string;
    of: string;
    fallbackNote: string;
    silent: string;
    speaking: string;
  };
}) {
  const [ordinal, setOrdinal] = useState(Math.max(0, data.turns.length - 1));
  const [use3D, setUse3D] = useState(false);
  const [reduced, setReduced] = useState(false);
  const [colours, setColours] = useState<Record<string, string>>({});
  const [variant, setVariant] = useState<Variant>("obsidian");

  /* The URL wins (?chamber=orrery, for comparing them side by side or grabbing
   * a screenshot), then the reader's saved preference. The table is the one
   * screen with a real aesthetic choice in it, so the choice is remembered. */
  useEffect(() => {
    const wanted = new URLSearchParams(window.location.search).get("chamber");
    if (wanted && VARIANTS.some((v) => v.id === wanted)) {
      setVariant(wanted as Variant);
      return;
    }
    try {
      const saved = window.localStorage.getItem("counsel-chamber");
      if (saved && VARIANTS.some((v) => v.id === saved)) setVariant(saved as Variant);
    } catch {
      /* Site data blocked. The default is fine. */
    }
  }, []);

  function chooseVariant(next: Variant) {
    setVariant(next);
    try {
      window.localStorage.setItem("counsel-chamber", next);
    } catch {
      /* Not remembering it is a smaller failure than refusing to change it. */
    }
  }

  useEffect(() => {
    const query = window.matchMedia("(prefers-reduced-motion: reduce)");
    const apply = () => {
      setReduced(query.matches);
      // Reduced motion still gets the 3D table if WebGL is there; what it loses
      // is the pulse, not the view. A reader who dislikes movement has not
      // asked to be shown less.
      setUse3D(isWebGLAvailable());
    };
    apply();
    query.addEventListener("change", apply);
    setColours(seatColours());
    return () => query.removeEventListener("change", apply);
  }, []);

  useEffect(() => setOrdinal(Math.max(0, data.turns.length - 1)), [data.turns.length]);

  const active = data.turns[ordinal];
  const speaking = active?.is_seat ? active.speaker : null;

  /* Edges are shown up to the scrubbed point, so replaying a debate builds the
     argument rather than showing its finished shape from the first frame. */
  const visibleEdges = useMemo(() => {
    const upTo = new Set(data.turns.slice(0, ordinal + 1).map((t) => t.turn_id));
    return data.edges.filter((e) => upTo.has(e.turn_id));
  }, [data.edges, data.turns, ordinal]);

  const lastSpokeAt = useMemo(() => {
    const at: Record<string, number> = {};
    data.turns.slice(0, ordinal + 1).forEach((t) => {
      if (t.is_seat) at[t.speaker] = t.ordinal;
    });
    return at;
  }, [data.turns, ordinal]);

  const titles = Object.fromEntries(data.seats.map((s) => [s.id, s.title]));

  return (
    <section className="chamber" aria-label="The round table">
      <div
        className="chamber-stage"
        data-mode={use3D ? "3d" : "svg"}
        /* The resolved hex the 3D scene is actually given. Exposed because the
         * colours reach three.js through a converter, not through CSS, and a
         * silent fallback to grey is exactly the kind of failure that looks
         * deliberate. A test asserts these are five distinct values. */
        data-colours={SEATS.map((s) => colours[s] ?? "").join(",")}
      >
        {use3D ? (
          <Table3D
            edges={visibleEdges}
            speaking={speaking}
            lastSpokeAt={lastSpokeAt}
            activeOrdinal={ordinal}
            colours={colours}
            reduced={reduced}
            variant={variant}
          />
        ) : (
          <TableSVG
            edges={visibleEdges}
            speaking={speaking}
            lastSpokeAt={lastSpokeAt}
            activeOrdinal={ordinal}
            titles={titles}
          />
        )}
      </div>

      {use3D ? (
        <div
          className="chamber-variants"
          role="group"
          aria-label="Table style"
          data-variant={variant}
        >
          {VARIANTS.map((v) => (
            <button
              key={v.id}
              type="button"
              className="lang"
              aria-pressed={variant === v.id}
              onClick={() => chooseVariant(v.id)}
            >
              {v.label}
            </button>
          ))}
        </div>
      ) : null}

      <p className="chamber-caption">{data.shows}</p>
      {!use3D ? <p className="chamber-caption">{labels.fallbackNote}</p> : null}

      {data.turns.length > 0 ? (
        <div className="replay">
          <label htmlFor="replay-scrub" className="replay-label">
            {labels.replay}
          </label>
          <input
            id="replay-scrub"
            type="range"
            min={0}
            max={data.turns.length - 1}
            value={ordinal}
            onChange={(e) => setOrdinal(Number(e.target.value))}
            data-testid="replay-scrub"
          />
          <p className="citation">
            <span className="span-ref">
              {labels.turn} {ordinal + 1} {labels.of} {data.turns.length}
            </span>
            <span className="arm" data-testid="replay-speaker">
              {speaking ? `${titles[speaking] ?? speaking} ${labels.speaking}` : labels.silent}
            </span>
            {active ? <span className="hash">{active.sig}</span> : null}
          </p>
          {active ? (
            <p className="passage" data-testid="replay-text">
              {active.text}
            </p>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}
