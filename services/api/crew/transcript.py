"""A transcript that cannot be quietly edited.

WHY A CHAIN AND NOT PER-MESSAGE SIGNATURES
------------------------------------------
COUNSEL's product is the record: a memo, a dissent log, and months later an
outcome ledger that says who was right. All of that is worthless if the
transcript behind it can be adjusted after the fact — and the most likely
adjustment is not an attacker but the owner, quietly improving what the CFO said
before showing it to someone.

Signing each turn independently would catch an edited turn and miss a deleted or
reordered one. So each signature covers the turn AND the previous signature,
which makes the transcript a hash chain: changing turn 2 of 5 invalidates 2, 3,
4 and 5, and removing a turn from the middle breaks everything after the gap.

WHAT THIS DOES NOT DEFEND AGAINST, STATED PLAINLY
-------------------------------------------------
The signing key lives beside the data. Anyone who can edit the database can also
read the key and re-sign a forged chain. This is tamper-EVIDENCE, not tamper-
proofing: it catches accidental corruption, a partial write, a well-meaning edit,
and any change made through the application rather than through the file. Making
it resist a determined operator would need the key held somewhere COUNSEL cannot
reach, which is a deployment decision and not a code one.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime

from services.api.rag.citations import Citation

GENESIS = "0" * 64


@dataclass(frozen=True)
class Turn:
    turn_id: str
    session_id: str
    round_no: int
    stage: str
    speaker: str
    text: str
    provider: str
    model: str
    citations: tuple[Citation, ...]
    created_at: str
    prev_sig: str
    sig: str

    def payload(self) -> dict[str, object]:
        """Exactly the fields the signature covers. `sig` is excluded because it
        is the output; everything else is input, including prev_sig."""
        return {
            "turn_id": self.turn_id,
            "session_id": self.session_id,
            "round_no": self.round_no,
            "stage": self.stage,
            "speaker": self.speaker,
            "text": self.text,
            "provider": self.provider,
            "model": self.model,
            "citations": [asdict(c) for c in self.citations],
            "created_at": self.created_at,
            "prev_sig": self.prev_sig,
        }


def canonical(payload: dict[str, object]) -> bytes:
    """Sorted keys, no whitespace, UTF-8 preserved.

    Canonicalisation is the part that is easy to get subtly wrong: if two
    serialisations of the same turn can differ, a valid transcript will
    intermittently fail to verify and the failure will look like tampering.
    """
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def sign(payload: dict[str, object], key: bytes) -> str:
    return hmac.new(key, canonical(payload), hashlib.sha256).hexdigest()


def session_key(conn=None) -> bytes:
    """The signing key, stable for the life of the installation.

    Order: COUNSEL_TRANSCRIPT_KEY if set, then a key generated once and stored
    in the database, then a per-process key for tests and in-memory use.

    The middle case exists because of a bug this had. A fresh key per process
    meant every restart made every past transcript fail verification — and fail
    it in exactly the way tampering does, so the Room would report "chain
    broken" after an ordinary deploy and a reader would have no way to tell the
    difference between a restarted server and an edited record. A verification
    that cries wolf on a restart is worse than none, because it teaches people
    to ignore it.

    This does not change what the signature defends against. The key sits beside
    the data either way; see the module docstring. It changes only whether a
    restart is mistaken for an attack.
    """
    configured = os.getenv("COUNSEL_TRANSCRIPT_KEY", "")
    if configured:
        return configured.encode()
    if conn is not None:
        row = conn.execute("SELECT value FROM instance WHERE key = 'transcript_key'").fetchone()
        if row is not None:
            return bytes.fromhex(row["value"] if hasattr(row, "keys") else row[0])
        generated = secrets.token_bytes(32)
        conn.execute(
            "INSERT OR IGNORE INTO instance(key, value) VALUES ('transcript_key', ?)",
            (generated.hex(),),
        )
        conn.commit()
        row = conn.execute("SELECT value FROM instance WHERE key = 'transcript_key'").fetchone()
        return bytes.fromhex(row["value"] if hasattr(row, "keys") else row[0])
    return _PROCESS_KEY


_PROCESS_KEY = secrets.token_bytes(32)


@dataclass
class Transcript:
    session_id: str
    key: bytes = field(default_factory=session_key)
    _turns: list[Turn] = field(default_factory=list)

    def append(
        self,
        *,
        round_no: int,
        stage: str,
        speaker: str,
        text: str,
        provider: str = "",
        model: str = "",
        citations: tuple[Citation, ...] = (),
        created_at: str | None = None,
    ) -> Turn:
        prev_sig = self._turns[-1].sig if self._turns else GENESIS
        turn = Turn(
            turn_id=f"{self.session_id}:{len(self._turns):04d}",
            session_id=self.session_id,
            round_no=round_no,
            stage=stage,
            speaker=speaker,
            text=text,
            provider=provider,
            model=model,
            citations=citations,
            created_at=created_at or datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            prev_sig=prev_sig,
            sig="",
        )
        signed = Turn(**{**asdict_shallow(turn), "sig": sign(turn.payload(), self.key)})
        self._turns.append(signed)
        return signed

    def adopt(self, turns: list[Turn]) -> None:
        """Load turns from storage without re-signing them, so verify() is
        checking what was stored rather than what was just recomputed."""
        self._turns = list(turns)

    def turns(self) -> list[Turn]:
        return list(self._turns)

    def verify(self) -> list[str]:
        """Return the ids of every turn that fails. Empty means intact.

        Reports ALL failures rather than the first, because the point of a chain
        is that one edit invalidates everything downstream, and a reviewer
        should see the extent of the damage rather than its first symptom.
        """
        broken: list[str] = []
        expected_prev = GENESIS
        for turn in self._turns:
            if turn.prev_sig != expected_prev or not hmac.compare_digest(
                turn.sig, sign(turn.payload(), self.key)
            ):
                broken.append(turn.turn_id)
                # The chain is already broken; every later turn inherits it.
                expected_prev = None  # type: ignore[assignment]
            else:
                expected_prev = turn.sig
        return broken


def asdict_shallow(turn: Turn) -> dict[str, object]:
    """asdict() deep-converts the Citation tuple into dicts, which would change
    the type on the way back in. This keeps the field values as they are."""
    return {f: getattr(turn, f) for f in turn.__dataclass_fields__}
