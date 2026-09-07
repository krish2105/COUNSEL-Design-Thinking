"""Sessions and turns on disk.

The important detail: `load_transcript` reads the stored signature bytes and
hands them to `Transcript.adopt` without re-signing. That is what makes
`/verify` meaningful — it checks the rows as they sit in the database, so an
edit made outside the application is exactly what it detects.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import UTC, datetime
from sqlite3 import Connection

from services.api.core.db import WRITE_LOCK
from services.api.crew.auditor import Flag
from services.api.crew.session import Session, Stage
from services.api.crew.transcript import Transcript, Turn, session_key
from services.api.rag.citations import Citation


def save_session(session: Session, *, conn: Connection) -> None:
    with WRITE_LOCK:
        conn.execute(
            "INSERT INTO sessions(session_id, question, stage, round_no, closed, ended_early, "
            "created_at) VALUES (?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(session_id) DO UPDATE SET stage=excluded.stage, "
            "round_no=excluded.round_no, closed=excluded.closed, ended_early=excluded.ended_early",
            (
                session.session_id,
                session.question,
                str(session.stage),
                session.round_no,
                int(session.closed),
                session.ended_early,
                datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            ),
        )
        conn.commit()


def save_turns(turns: list[Turn], *, conn: Connection, start_ordinal: int) -> None:
    with WRITE_LOCK:
        conn.executemany(
            "INSERT OR IGNORE INTO turns(turn_id, session_id, ordinal, round_no, stage, speaker, "
            "text, provider, model, citations, created_at, prev_sig, sig) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    t.turn_id,
                    t.session_id,
                    start_ordinal + i,
                    t.round_no,
                    t.stage,
                    t.speaker,
                    t.text,
                    t.provider,
                    t.model,
                    json.dumps([asdict(c) for c in t.citations]),
                    t.created_at,
                    t.prev_sig,
                    t.sig,
                )
                for i, t in enumerate(turns)
            ],
        )
        conn.commit()


def save_flags(flags: list[Flag], *, conn: Connection) -> None:
    if not flags:
        return
    with WRITE_LOCK:
        conn.executemany(
            "INSERT OR IGNORE INTO turn_flags(turn_id, rule, severity, excerpt, why) "
            "VALUES (?, ?, ?, ?, ?)",
            [(f.turn_id, f.rule, f.severity, f.excerpt, f.why) for f in flags],
        )
        conn.commit()


def load_session(session_id: str, *, conn: Connection) -> Session | None:
    row = conn.execute("SELECT * FROM sessions WHERE session_id = ?", (session_id,)).fetchone()
    if row is None:
        return None
    session = Session(
        session_id=row["session_id"],
        question=row["question"],
        stage=Stage(row["stage"]),
        round_no=row["round_no"],
        signing_key=session_key(conn),
    )
    session.closed = bool(row["closed"])
    session.ended_early = row["ended_early"]
    session.transcript = load_transcript(session_id, conn=conn)
    return session


def load_transcript(session_id: str, *, conn: Connection) -> Transcript:
    transcript = Transcript(session_id=session_id, key=session_key(conn))
    rows = conn.execute(
        "SELECT * FROM turns WHERE session_id = ? ORDER BY ordinal", (session_id,)
    ).fetchall()
    transcript.adopt(
        [
            Turn(
                turn_id=r["turn_id"],
                session_id=r["session_id"],
                round_no=r["round_no"],
                stage=r["stage"],
                speaker=r["speaker"],
                text=r["text"],
                provider=r["provider"],
                model=r["model"],
                citations=tuple(Citation(**c) for c in json.loads(r["citations"])),
                created_at=r["created_at"],
                prev_sig=r["prev_sig"],
                sig=r["sig"],
            )
            for r in rows
        ]
    )
    return transcript


def turn_count(session_id: str, *, conn: Connection) -> int:
    return conn.execute(
        "SELECT COUNT(*) FROM turns WHERE session_id = ?", (session_id,)
    ).fetchone()[0]


def flags_for(session_id: str, *, conn: Connection) -> dict[str, list[dict[str, str]]]:
    rows = conn.execute(
        "SELECT f.* FROM turn_flags f JOIN turns t ON t.turn_id = f.turn_id "
        "WHERE t.session_id = ? ORDER BY t.ordinal",
        (session_id,),
    ).fetchall()
    out: dict[str, list[dict[str, str]]] = {}
    for r in rows:
        out.setdefault(r["turn_id"], []).append(
            {"rule": r["rule"], "severity": r["severity"], "excerpt": r["excerpt"], "why": r["why"]}
        )
    return out


def save_artefacts(session_id: str, kind: str, artefacts: dict, *, conn: Connection) -> None:
    """Stage artefacts, stored as JSON keyed by seat.

    Kept whole rather than exploded into columns: they are model output with a
    schema that will change as the stages do, and the memo reads them back as
    objects anyway.
    """
    with WRITE_LOCK:
        conn.execute(
            "INSERT INTO artefacts(session_id, kind, payload, created_at) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(session_id, kind) DO UPDATE SET payload=excluded.payload, "
            "created_at=excluded.created_at",
            (
                session_id,
                kind,
                json.dumps(
                    {
                        seat: [a.model_dump() for a in v] if isinstance(v, list) else v.model_dump()
                        for seat, v in artefacts.items()
                    },
                    ensure_ascii=False,
                ),
                datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            ),
        )
        conn.commit()


def load_artefacts(session_id: str, kind: str, *, conn: Connection) -> dict | None:
    row = conn.execute(
        "SELECT payload FROM artefacts WHERE session_id = ? AND kind = ?", (session_id, kind)
    ).fetchone()
    return json.loads(row["payload"]) if row else None


def save_evidence(session_id: str, evidence: list, *, conn: Connection) -> None:
    with WRITE_LOCK:
        conn.executemany(
            "INSERT OR REPLACE INTO evidence(session_id, evidence_id, summary, source, external) "
            "VALUES (?, ?, ?, ?, ?)",
            [(session_id, e.evidence_id, e.summary, e.source, int(e.external)) for e in evidence],
        )
        conn.commit()


def load_evidence(session_id: str, *, conn: Connection) -> list:
    from services.api.crew.stages import Evidence

    return [
        Evidence(r["evidence_id"], r["summary"], r["source"], bool(r["external"]))
        for r in conn.execute(
            "SELECT * FROM evidence WHERE session_id = ? ORDER BY evidence_id", (session_id,)
        ).fetchall()
    ]


def list_sessions(*, conn: Connection) -> list[dict[str, object]]:
    return [
        dict(r)
        for r in conn.execute(
            "SELECT s.*, (SELECT COUNT(*) FROM turns t WHERE t.session_id = s.session_id) "
            "AS n_turns FROM sessions s ORDER BY s.created_at DESC"
        ).fetchall()
    ]
