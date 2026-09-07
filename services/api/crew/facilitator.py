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

#: How many past rounds each seat is shown in full. Everything older is
#: compressed to one line per seat.
#:
#: Measured before this existed: every seat was handed the ENTIRE transcript
#: every round, so the history grew 111 -> 931 -> 1776 tokens and a round grew
#: 18.1s -> 29.9s -> 34.2s. Five seats re-processing 1776 tokens is ~9k tokens
#: of prompt work per round, and it compounds every round after.
#:
#: One round of full context is also the honest amount. A facilitated round
#: means arguing against the state at the end of the previous round; nobody in
#: a real boardroom re-reads round one verbatim before speaking in round five.
HISTORY_ROUNDS = 1
#: Characters of an older turn kept in the running summary.
SUMMARY_CHARS = 160
#: How many older turns the summary carries at most. Without this the summary
#: itself grows one line per turn forever — slower than the full transcript
#: did, but still linear, which is the same bug with a smaller constant.
SUMMARY_TURNS = 10


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

        Bounded, not complete. The most recent HISTORY_ROUNDS rounds are given
        in full; anything older is one clipped line per turn. Without this the
        prompt grew every round and so did the wall clock (see HISTORY_ROUNDS).
        """
        turns = session.transcript.turns()
        if not turns:
            return "The room has not spoken yet. Open the argument."

        cutoff = max(0, session.round_no - HISTORY_ROUNDS)
        recent = [t for t in turns if t.round_no > cutoff]
        # The Facilitator's opening turn is round 0 and carries the question and
        # the stage rules, so it is always kept. Dropping it left round 1 with an
        # EMPTY history — the seats opened the argument having been told nothing
        # about it beyond their own system prompt.
        opening = [t for t in turns if t.round_no == 0]
        summarised = [t for t in turns if 0 < t.round_no <= cutoff and t.speaker in SEATING]
        dropped = max(0, len(summarised) - SUMMARY_TURNS)
        older = opening + summarised[-SUMMARY_TURNS:]

        blocks = []
        if older:
            preamble = "Earlier rounds, in brief:"
            if dropped:
                # Said out loud rather than silently truncated: a seat should
                # know the record is longer than what it was handed.
                preamble += f" ({dropped} earlier turn(s) omitted)"
            blocks.append(
                preamble
                + "\n"
                + "\n".join(
                    f"- [round {t.round_no}] {t.speaker.upper()}: "
                    f"{t.text[:SUMMARY_CHARS].rstrip()}..."
                    for t in older
                )
            )
        if recent:
            blocks.append(
                "The round you are answering:\n\n"
                + "\n\n".join(f"[round {t.round_no}] {t.speaker.upper()}: {t.text}" for t in recent)
            )
        return (
            "\n\n".join(blocks) if blocks else ("The room has not spoken yet. Open the argument.")
        )
