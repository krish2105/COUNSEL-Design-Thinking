"""The round table, derived from the record rather than authored.

WHY THE GEOMETRY COMES FROM THE TRANSCRIPT
------------------------------------------
Everything the chamber draws is computed from turns that are already signed:
who spoke, in what order, and who they addressed. There are no model files, no
textures, no positions stored anywhere. That is not a size optimisation — it
means the picture cannot disagree with the record. A chamber loaded from its own
saved state could drift from the transcript it claims to show; this one cannot,
because it has no state of its own.

WHERE THE EDGES COME FROM
-------------------------
A turn does not carry an addressee — the mandates write prose, not routing
headers. So an edge is derived: when the CFO's turn names the COO, an edge runs
cfo -> coo. Deterministic, checkable by reading the turn, and honest about being
a derivation rather than a declaration.

WHAT THIS DELIBERATELY DOES NOT DO
----------------------------------
It does not infer agreement, sentiment or intensity. An edge means "this seat
named that seat", nothing more. Drawing a thicker line for a stronger objection
would be inventing a measurement the transcript does not contain, and the 3D
view is exactly where an invented measurement would be least questioned.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from sqlite3 import Connection

from services.api.crew.mandate import SEATING, load_mandates

#: What a seat can be called in prose. Ordered longest-first so "Chief Financial
#: Officer" is matched before a bare "CFO" inside it.
ALIASES: dict[str, tuple[str, ...]] = {
    "cfo": ("chief financial officer", "cfo"),
    "cmo": ("chief marketing officer", "cmo"),
    "coo": ("chief operating officer", "coo"),
    "ethics": ("ethics officer", "the ethics"),
    "devil": ("devil's advocate", "devil’s advocate", "devils advocate"),
}


@dataclass(frozen=True)
class Edge:
    from_seat: str
    to_seat: str
    turn_id: str
    round_no: int


def addressees(text: str, *, speaker: str) -> tuple[str, ...]:
    """Which seats this turn names. Never the speaker itself."""
    lowered = text.lower()
    found = []
    for seat, aliases in ALIASES.items():
        if seat == speaker:
            # A seat naming itself is not an argument between two people, and a
            # self-edge on a round table is a circle nobody can read.
            continue
        if any(re.search(rf"(?<![a-z]){re.escape(a)}(?![a-z])", lowered) for a in aliases):
            found.append(seat)
    return tuple(sorted(found, key=SEATING.index))


def edges(turns) -> list[Edge]:
    return [
        Edge(from_seat=t.speaker, to_seat=to, turn_id=t.turn_id, round_no=t.round_no)
        for t in turns
        if t.speaker in SEATING
        for to in addressees(t.text, speaker=t.speaker)
    ]


def chamber_state(session_id: str, *, conn: Connection) -> dict[str, object]:
    """Everything the chamber needs, and nothing it does not."""
    from services.api.crew.store import load_transcript

    transcript = load_transcript(session_id, conn=conn)
    turns = transcript.turns()
    mandates = load_mandates()
    spoken = [t for t in turns if t.speaker in SEATING]

    return {
        "session_id": session_id,
        "seats": [
            {"id": seat, "title": mandates[seat].title, "index": i}
            for i, seat in enumerate(SEATING)
        ],
        "turns": [
            {
                "turn_id": t.turn_id,
                "ordinal": i,
                "round_no": t.round_no,
                "stage": t.stage,
                "speaker": t.speaker,
                "text": t.text,
                "is_seat": t.speaker in SEATING,
                "sig": t.sig[:16],
            }
            for i, t in enumerate(turns)
        ],
        "edges": [e.__dict__ for e in edges(turns)],
        "rounds": sorted({t.round_no for t in spoken}),
        "chain_intact": transcript.verify() == [],
        "shows": (
            "Seats, speaking order, and which seats named which. An edge means one seat "
            "named another in that turn — not that it agreed, objected, or how strongly. "
            "Nothing here is inferred beyond that."
        ),
    }
