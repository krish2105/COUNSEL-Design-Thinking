# COUNSEL Phase D Implementation Plan — the chamber and the remaining tabs

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans, inline, no subagents. One conventional commit per task with the Claude co-author trailer.

**Goal:** The one loud moment — a 3D round table you can scrub through a debate on — plus the tabs that make the record navigable, the last two of the owner's chosen extras, and a Playwright journey that walks the whole product end to end.

**Architecture:** The chamber is derived entirely from the signed transcript. No geometry files, no textures, no external assets: five seats on a circle, edges from who addressed whom, glow from turn recency. `frameloop="demand"` so it renders on scrub and on new turns, not sixty times a second. An SVG round table is a real fallback, not a placeholder — it is what renders under `prefers-reduced-motion`, without WebGL, and in the printed report, and it is the source of truth for the report figure so the picture in the docx matches the picture on screen.

**Tech Stack:** R3F 9 + drei 10 + three 0.185 (already installed), Motion 13, and the Web Speech / `say` path for per-agent voice.

## Global Constraints

Everything from Phases A–C holds. Additionally:

- **The chamber must work without WebGL.** Progressive enhancement is mandatory, and the fallback must look intentional rather than broken.
- **`prefers-reduced-motion` disables the glow pulse and the camera drift**, and the replay still works.
- **No agent gains a tool**; the B3 registry assertion still passes.
- **Voice is local and free** — no cloud TTS, no key, no audio leaves the machine.
- Contrast floors still apply, and the chamber's own text is measured like everything else.

---

## Task D1: The round table

**Files:** `apps/web/components/chamber/{Chamber.tsx,Table3D.tsx,TableSVG.tsx,useChamberData.ts}`, `apps/web/lib/chamber.ts`, `tests/crew/test_chamber.py` (the addressee derivation lives server-side so the report can use it too).

**Interfaces:**
```python
# services/api/crew/chamber.py
@dataclass(frozen=True)
class Edge:
    from_seat: str
    to_seat: str
    turn_id: str
    round_no: int

def addressees(text: str, *, speaker: str) -> tuple[str, ...]   # who this turn names
def edges(turns) -> list[Edge]
def chamber_state(session_id, *, conn) -> dict                   # seats, edges, turn order
```
```ts
// apps/web/lib/chamber.ts
export const SEAT_ANGLES: Record<Seat, number>   // fixed, so a replay seats the same people
export function seatPosition(seat: Seat, radius: number): [number, number, number]
export function arc(from: Seat, to: Seat, radius: number): [number, number, number][]
```

- [ ] **Step 1:** Server tests — a turn naming "the CFO" produces an edge to `cfo`; a turn naming nobody produces none; a seat naming *itself* produces no self-edge; the derivation is deterministic.
- [ ] **Step 2:** Implement `chamber.py` and `/sessions/{id}/chamber`. Run — PASS.
- [ ] **Step 3:** Build `Table3D` (R3F, `frameloop="demand"`) and `TableSVG`. `Chamber` picks between them on WebGL support and reduced-motion.
- [ ] **Step 4:** Commit `feat(web): the chamber — a round table derived from the signed transcript`.

**Verifiable check:** the SVG fallback renders five seats and the same edges as the 3D view, asserted in Playwright by comparing edge counts.

---

## Task D2: Replay

**Files:** `apps/web/components/chamber/Replay.tsx`, wired into the Room.

- [ ] **Step 1:** Playwright — the slider moves through the transcript, the visible turn changes with it, and the chamber's active seat follows.
- [ ] **Step 2:** Implement. A scrub sets the active turn; the chamber re-renders on demand.
- [ ] **Step 3:** Commit `feat(web): scrub a debate through the chamber`.

**Verifiable check:** moving the slider changes both the highlighted seat and the turn shown, asserted in a browser.

---

## Task D3: Stages, Board, Crew and Report tabs

**Files:** `apps/web/app/{stages,board,crew,report}/page.tsx`.

- Stages: the Empathise → Learn stepper, showing which rules bind at each and what the room produced.
- Board: framings and ideas as cards in the margin rail, by seat.
- Crew: the mandates, their blind spots, their granted tools, and the capability table — the honest page.
- Report: everything assembled, with an export the *user* performs.

- [ ] **Step 1:** Playwright per tab: renders, axe clean, no overflow, RTL holds.
- [ ] **Step 2:** Implement. **Step 3:** Commit `feat(web): stages, board, crew and report tabs`.

**Verifiable check:** every tab in the master plan's §3.6 list exists and is reachable from the masthead.

---

## Task D4: Per-agent voice

**Files:** `apps/web/lib/voice.ts`, wired into the Room.

Web Speech API — in the browser, free, offline on macOS, no key and no audio leaving the machine. A distinct voice per mandate, chosen deterministically from the available voice list so the CFO sounds the same every session.

- [ ] **Step 1:** Tests — voice assignment is deterministic and distinct per seat; the feature is off by default and degrades silently where the API is absent.
- [ ] **Step 2:** Implement with an explicit toggle. **Step 3:** Commit `feat(web): a distinct offline voice per mandate`.

**Verifiable check:** five seats map to five distinct voices where available, and nothing throws where the API is missing.

---

## Task D5: Live red-team theatre

**Files:** `apps/web/app/security/page.tsx`, `services/api/routers/security.py`.

A button that poisons a document mid-session and shows the Auditor catching it and the memo refusing it — the Phase E harness made watchable.

- [ ] **Step 1:** API test — a poisoned document is ingested, flagged, and its injected instruction never reaches a memo claim.
- [ ] **Step 2:** Implement. **Step 3:** Commit `feat(security): the red-team demonstration, live`.

**Verifiable check:** the demo shows a flagged document and an unchanged recommendation, in the browser.

---

## Task D6: The full journey

**Files:** `apps/web/e2e/journey.spec.ts`.

Upload → define → debate → memo → outcome, in one Playwright test on the stub-backed API.

- [ ] Commit `test(e2e): the whole product, once, end to end`.

**Verifiable check:** the journey passes on desktop and mobile.

---

## Task D7: Phase D documentation

- [ ] `docs/chamber.md` — what the 3D view shows, what it cannot show, and how normalisation stops it misleading.
- [ ] README updated; `make check` and `make e2e` green; placeholder scan clean.
- [ ] Commit `docs: what the chamber shows and where it could mislead`.
