"use client";

/* THE DISSENT MARGIN.
 *
 * COUNSEL's signature element, and the reason the Record surface is a text
 * column rather than a grid of cards. Every entry in the record is set against
 * a narrow left rail, and anything that annotates that entry lives IN the rail
 * — the way a lawyer's marginalia sit beside a clause rather than beneath it.
 *
 * In Phase A the rail carries citation anchors and language marks. In Phase C
 * the same rail carries dissent marks in the dissenting agent's seat colour,
 * and in Phase E it carries calibration marks once the outcome ledger knows who
 * turned out to be right. One element, three jobs, all of them the same job:
 * saying who said this and whether to believe it.
 *
 * `seat` is the seam. It is unset in Phase A because there are no agents yet. */

export type Seat = "cfo" | "cmo" | "coo" | "ethics" | "devil";

export function RailEntry({
  mark,
  note,
  seat,
  children,
}: {
  mark: string;
  note?: string;
  seat?: Seat;
  children: React.ReactNode;
}) {
  return (
    <article className="rail-entry" data-seat={seat}>
      <aside className="rail" aria-hidden={!note}>
        <span className="rail-mark">{mark}</span>
        {note ? <span className="rail-note">{note}</span> : null}
      </aside>
      <div className="rail-body">{children}</div>
    </article>
  );
}
