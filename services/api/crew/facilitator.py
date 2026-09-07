"""Turn-taking, in Python.

WHY THE RUNTIME IS DETERMINISTIC AND ONLY THE SPEECH IS NOT
-----------------------------------------------------------
Who speaks, in what order, for how many rounds, and when the argument ends are
all decided here in ordinary code. The model produces only what a given seat
says on its turn. That split is deliberate: a debate whose control flow is
itself model-generated cannot be replayed, cannot be bounded, and cannot be
audited — you would be debugging a conversation instead of a program.

WHY THE FIVE SEATS SPEAK CONCURRENTLY
-------------------------------------
Measured on qwen3:8b: 22.5 tokens/s, so a 180-token turn is roughly 8 seconds.
Fifteen sequential mandate turns plus overhead is about 3 minutes, inside the
4-minute target (§3.8) with almost no headroom.

Running the five seats of a round concurrently is not a shortcut, it is what the
round already means: every seat argues against the transcript as it stood at the
END of the previous round, so no seat can hear another's current-round turn even
in principle. Sequential execution would create a hidden advantage for whoever
spoke last, which is precisely the bias a facilitated round exists to remove.

Turns are collected concurrently and then written to the transcript in fixed
SEATING order, so the record — and its hash chain — is identical every run
regardless of which model finished first.
"""

from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed

from services.api.core import killswitch
from services.api.core.llm import LLMChain, Message
from services.api.crew.mandate import SEATING, load_mandates, system_prompt
from services.api.crew.session import Session, Stage
from services.api.crew.transcript import Turn

MAX_TURN_TOKENS = 180
MAX_ROUNDS = 6


class Facilitator:
    def __init__(self, llm: LLMChain, *, max_turn_tokens: int = MAX_TURN_TOKENS) -> None:
        self.llm = llm
        self.max_turn_tokens = max_turn_tokens

    def open(
        self,
        session_id: str,
        question: str,
        *,
        stage: Stage = Stage.DEFINE,
        signing_key: bytes | None = None,
    ) -> Session:
        session = Session(
            session_id=session_id, question=question, stage=stage, signing_key=signing_key
        )
        session.transcript.append(
            round_no=0,
            stage=str(stage),
            speaker="facilitator",
            text=(
                f"Session opened. The decision before the room: {question} "
                f"Stage: {stage}. Rules in force: " + " ".join(session.rules)
            ),
        )
        return session

    def run_round(
        self,
        session: Session,
        *,
        speakers: tuple[str, ...] = SEATING,
        on_progress: Callable[[str, str], None] | None = None,
    ) -> list[Turn]:
        """One round. Returns the mandate turns, in seating order.

        `on_progress(seat, text)` fires the moment a seat finishes, in whatever
        order the models complete. It exists so a viewer can watch the room
        think rather than wait forty seconds for a block of JSON — and it is
        deliberately separate from the returned turns, which stay in seating
        order because the hash chain depends on them being identical every run.
        """
        if session.closed:
            raise RuntimeError(f"session {session.session_id} is closed")
        killswitch.check()

        session.round_no += 1
        history = self._history(session)
        mandates = load_mandates()

        def speak(seat: str):
            mandate = mandates[seat]
            system = system_prompt(
                mandate,
                stage=str(session.stage),
                rules=session.rules,
                question=session.question,
            )
            return self.llm.complete(
                system,
                [Message("user", history)],
                max_tokens=self.max_turn_tokens,
                temperature=0.3,
                speaker=seat,
            )

        # A worker per seat: these are network-bound, and five is the whole room.
        responses = {}
        with ThreadPoolExecutor(max_workers=len(speakers)) as pool:
            futures = {pool.submit(speak, seat): seat for seat in speakers}
            for future in as_completed(futures):
                seat = futures[future]
                responses[seat] = future.result()
                if on_progress is not None:
                    on_progress(seat, responses[seat].text.strip())

        # Written in fixed seating order so the record and its hash chain are
        # identical every run, whatever order the models happened to finish in.
        turns = [
            session.transcript.append(
                round_no=session.round_no,
                stage=str(session.stage),
                speaker=seat,
                text=responses[seat].text.strip(),
                provider=responses[seat].provider,
                model=responses[seat].model,
            )
            for seat in speakers
        ]

        if any(r.provider == "stub" for r in responses.values()) and not all(
            r.provider == "stub" for r in responses.values()
        ):
            session.ended_early = (
                "some seats degraded to the deterministic stub mid-round; "
                "this round mixes model output with placeholder output"
            )
        return turns

    def interject(self, session: Session, text: str) -> Turn:
        """The human speaking as Chair, mid-session.

        Recorded as a turn like any other and signed into the same chain, so the
        record shows exactly where a person changed the room's direction. The
        Chair is a participant in the transcript, not an editor of it.
        """
        killswitch.check()
        return session.transcript.append(
            round_no=session.round_no,
            stage=str(session.stage),
            speaker="chair",
            text=text.strip(),
        )

    def advance(self, session: Session, stage: Stage) -> Session:
        session.stage = stage
        session.transcript.append(
            round_no=session.round_no,
            stage=str(stage),
            speaker="facilitator",
            text=f"Stage advanced to {stage}. Rules now in force: " + " ".join(session.rules),
        )
        return session

    def close(self, session: Session) -> Session:
        session.closed = True
        session.transcript.append(
            round_no=session.round_no,
            stage=str(session.stage),
            speaker="facilitator",
            text=f"Session closed after {session.round_no} round(s).",
        )
        return session

    def _history(self, session: Session) -> str:
        """The transcript as the room saw it at the end of the previous round.

        Turns from the CURRENT round are excluded by construction — run_round
        builds this before any seat speaks — which is what makes concurrent
        speaking equivalent to sequential speaking rather than a shortcut.
        """
        lines = [
            f"[round {t.round_no}] {t.speaker.upper()}: {t.text}"
            for t in session.transcript.turns()
        ]
        return "\n\n".join(lines) if lines else "The room has not spoken yet. Open the argument."
