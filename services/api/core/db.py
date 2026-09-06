"""SQLite with sqlite-vec. One file, no server, no account.

WHY NOT POSTGRES + PGVECTOR
---------------------------
COUNSEL's corpus is a handful of documents a person uploaded before a meeting,
plus the transcripts of their own debates. That is thousands of rows, not
millions. A managed Postgres would add an account, a network hop and a cold
start to a workload that fits comfortably in a file on a disk — and the free
tier of every managed option sleeps, which is exactly the wrong failure mode
for a demo.

TWO VECTOR SPACES, TWO TABLES
-----------------------------
The local embedder is 1024-dim and the deployed one is 384-dim (see
docs/models.md). A vec0 table has a fixed width, so each space gets its own
table — `vectors_1024`, `vectors_384` — created on demand. Making the width part
of the table name means a query can only ever reach vectors of its own width;
mixing spaces is not a bug that can happen here, it is a table that does not
exist.
"""

from __future__ import annotations

import sqlite3
import threading
from pathlib import Path

import sqlite_vec

#: Held around every write. FastAPI serves sync endpoints from a threadpool, so
#: a process-wide connection is touched by many threads. Python's sqlite3 is
#: thread-safe at the C level, but transaction state on a shared connection is
#: not — two interleaved write transactions can commit each other's work. One
#: operator means contention here is effectively zero, so a lock is the cheap
#: correct answer rather than a bottleneck.
WRITE_LOCK = threading.RLock()

SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    doc_id      TEXT PRIMARY KEY,      -- sha256 of the file bytes
    filename    TEXT NOT NULL,
    media_type  TEXT NOT NULL,
    text        TEXT NOT NULL,         -- the extracted text chunk offsets index into
    n_chars     INTEGER NOT NULL,
    ingested_at TEXT NOT NULL,
    trust       TEXT NOT NULL CHECK (trust = 'untrusted')
);

CREATE TABLE IF NOT EXISTS chunks (
    chunk_id  TEXT PRIMARY KEY,
    doc_id    TEXT NOT NULL REFERENCES documents(doc_id) ON DELETE CASCADE,
    ordinal   INTEGER NOT NULL,
    text      TEXT NOT NULL,
    start     INTEGER NOT NULL,
    end       INTEGER NOT NULL,
    lang      TEXT NOT NULL,
    trust     TEXT NOT NULL CHECK (trust = 'untrusted'),
    UNIQUE (doc_id, ordinal)
);
CREATE INDEX IF NOT EXISTS idx_chunks_doc ON chunks(doc_id);

-- Which vec0 row holds which chunk, in which space. The model_key is what stops
-- a 384-dim query from being answered out of a 1024-dim index.
CREATE TABLE IF NOT EXISTS vector_index (
    chunk_id  TEXT NOT NULL REFERENCES chunks(chunk_id) ON DELETE CASCADE,
    model_key TEXT NOT NULL,
    dim       INTEGER NOT NULL,
    vec_rowid INTEGER NOT NULL,
    PRIMARY KEY (chunk_id, model_key)
);
CREATE INDEX IF NOT EXISTS idx_vector_model ON vector_index(model_key);

-- What the untrusted-content scanner found in an uploaded document. Recorded
-- at ingest so the Data tab can show it and Phase E's harness can assert on it,
-- rather than being computed again at every prompt build.
CREATE TABLE IF NOT EXISTS doc_findings (
    doc_id      TEXT NOT NULL REFERENCES documents(doc_id) ON DELETE CASCADE,
    pattern     TEXT NOT NULL,
    severity    TEXT NOT NULL,
    start       INTEGER NOT NULL,
    end         INTEGER NOT NULL,
    excerpt     TEXT NOT NULL,
    PRIMARY KEY (doc_id, start, pattern)
);

CREATE TABLE IF NOT EXISTS sessions (
    session_id  TEXT PRIMARY KEY,
    question    TEXT NOT NULL,
    stage       TEXT NOT NULL,
    round_no    INTEGER NOT NULL,
    closed      INTEGER NOT NULL DEFAULT 0,
    ended_early TEXT,
    created_at  TEXT NOT NULL
);

-- Turns are stored exactly as signed. verify() reads THESE rows, so it is
-- checking what was persisted rather than what was just recomputed in memory —
-- which is the only version of the check that means anything.
CREATE TABLE IF NOT EXISTS turns (
    turn_id       TEXT PRIMARY KEY,
    session_id    TEXT NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    ordinal       INTEGER NOT NULL,
    round_no      INTEGER NOT NULL,
    stage         TEXT NOT NULL,
    speaker       TEXT NOT NULL,
    text          TEXT NOT NULL,
    provider      TEXT NOT NULL,
    model         TEXT NOT NULL,
    citations     TEXT NOT NULL,
    created_at    TEXT NOT NULL,
    prev_sig      TEXT NOT NULL,
    sig           TEXT NOT NULL,
    UNIQUE (session_id, ordinal)
);
CREATE INDEX IF NOT EXISTS idx_turns_session ON turns(session_id, ordinal);

CREATE TABLE IF NOT EXISTS turn_flags (
    turn_id  TEXT NOT NULL REFERENCES turns(turn_id) ON DELETE CASCADE,
    rule     TEXT NOT NULL,
    severity TEXT NOT NULL,
    excerpt  TEXT NOT NULL,
    why      TEXT NOT NULL,
    PRIMARY KEY (turn_id, rule)
);

-- What the room predicted, and what actually happened. The Learn stage.
CREATE TABLE IF NOT EXISTS outcomes (
    session_id  TEXT PRIMARY KEY REFERENCES sessions(session_id) ON DELETE CASCADE,
    chosen      TEXT NOT NULL,      -- what the room recommended
    actual      TEXT NOT NULL,      -- what turned out to be right, in hindsight
    notes       TEXT NOT NULL,
    recorded_at TEXT NOT NULL
);

-- One row per seat per session: which option it backed and how sure it was.
-- Written at Decide, scored at Learn. Confidence is stored at prediction time
-- and never rewritten, which is the entire point of a calibration record.
CREATE TABLE IF NOT EXISTS predictions (
    session_id TEXT NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    seat       TEXT NOT NULL,
    option     TEXT NOT NULL,
    confidence REAL NOT NULL,
    PRIMARY KEY (session_id, seat, option)
);

CREATE TABLE IF NOT EXISTS artefacts (
    session_id TEXT NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    kind       TEXT NOT NULL,      -- framing | idea | score | dissent
    payload    TEXT NOT NULL,      -- JSON, keyed by seat
    created_at TEXT NOT NULL,
    PRIMARY KEY (session_id, kind)
);

CREATE TABLE IF NOT EXISTS evidence (
    session_id  TEXT NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    evidence_id TEXT NOT NULL,
    summary     TEXT NOT NULL,
    source      TEXT NOT NULL,
    external    INTEGER NOT NULL DEFAULT 1,
    PRIMARY KEY (session_id, evidence_id)
);

CREATE TABLE IF NOT EXISTS quotas (
    provider TEXT PRIMARY KEY,
    used     INTEGER NOT NULL
);
"""


def connect(path: str | Path = ":memory:") -> sqlite3.Connection:
    if path != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    # FastAPI runs sync path operations in a threadpool, so the connection is
    # legitimately used from more than one thread. Writes are serialised by
    # WRITE_LOCK above.
    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    conn.enable_load_extension(False)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)
    conn.commit()
    return conn


def vector_table(dim: int) -> str:
    return f"vectors_{dim}"


def ensure_vector_table(conn: sqlite3.Connection, dim: int) -> str:
    name = vector_table(dim)
    conn.execute(f"CREATE VIRTUAL TABLE IF NOT EXISTS {name} USING vec0(embedding float[{dim}])")
    conn.commit()
    return name
