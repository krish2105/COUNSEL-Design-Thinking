"use client";

/* The round table, in two dimensions.
 *
 * This is NOT a placeholder for the 3D view. It is what renders under
 * prefers-reduced-motion, on a machine without WebGL, and in the printed
 * report — and because the report figure comes from here, the picture in the
 * document is the same picture as the one on screen, drawn from the same
 * numbers. A fallback that looked different would quietly make the report a
 * second source of truth.
 *
 * It also draws the same edges from the same data, which is what lets a test
 * compare the two views by counting them.
 */

import { SEATS, arcPoints, glow, seatXZ, type Seat } from "@/lib/chamber";

export type ChamberEdge = { from_seat: string; to_seat: string; turn_id: string };

const R = 34;
const VIEW = 100;

export function TableSVG({
  edges,
  speaking,
  lastSpokeAt,
  activeOrdinal,
  titles,
}: {
  edges: ChamberEdge[];
  speaking: string | null;
  lastSpokeAt: Record<string, number>;
  activeOrdinal: number;
  titles: Record<string, string>;
}) {
  const unique = Array.from(
    new Map(edges.map((e) => [`${e.from_seat}-${e.to_seat}`, e])).values(),
  ).filter((e) => SEATS.includes(e.from_seat as Seat) && SEATS.includes(e.to_seat as Seat));

  return (
    <svg
      viewBox={`${-VIEW / 2} ${-VIEW / 2} ${VIEW} ${VIEW}`}
      className="table-svg"
      role="img"
      aria-label={
        speaking
          ? `The round table. ${titles[speaking] ?? speaking} is speaking.`
          : "The round table, with five seats."
      }
      data-testid="table-svg"
    >
      {/* The table itself: a ring, not a disc. A filled circle would read as an
          object; a ring reads as a place people sit around. */}
      <circle r={R} className="table-ring" />
      <circle r={R * 0.62} className="table-inner" />

      <g className="table-edges">
        {unique.map((e) => {
          const pts = arcPoints(e.from_seat as Seat, e.to_seat as Seat, R * 0.86);
          return (
            <polyline
              key={`${e.from_seat}-${e.to_seat}`}
              points={pts.map(([x, z]) => `${x},${z}`).join(" ")}
              data-from={e.from_seat}
              data-to={e.to_seat}
              data-testid="table-edge"
            />
          );
        })}
      </g>

      {SEATS.map((seat) => {
        const [x, z] = seatXZ(seat, R);
        const lit = glow(lastSpokeAt[seat] ?? null, activeOrdinal);
        const isSpeaking = speaking === seat;
        return (
          <g key={seat} data-seat={seat} data-testid="table-seat" transform={`translate(${x} ${z})`}>
            {/* The halo carries the glow so the seat mark keeps a constant size —
                a seat that grows while speaking reads as gaining importance. */}
            <circle r={7.4} className="seat-halo" style={{ opacity: lit * 0.55 }} />
            <circle r={4.2} className="seat-mark" data-speaking={isSpeaking || undefined} />
            <text y={0.9} className="seat-label">
              {seat === "ethics" ? "ETH" : seat === "devil" ? "DEV" : seat.toUpperCase()}
            </text>
          </g>
        );
      })}
    </svg>
  );
}
