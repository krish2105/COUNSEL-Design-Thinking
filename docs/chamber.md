# The chamber

The 3D round table: what it shows, what it deliberately does not, and where a
picture like this could mislead.

---

## What it is

Five abstract forms around a lit ring. A seat glows when it speaks and fades over
the turns after; an arc runs between two seats when one named the other; a slider
scrubs the whole debate.

**All of it is computed from the signed transcript.** There are no model files,
no textures, and no stored positions — the chamber has no state of its own. That
is not a size optimisation. A view loaded from its own saved state could drift
from the record it claims to show; this one cannot.

## What an edge means, and what it does not

An edge means **one seat named another in that turn**. Nothing else.

It does not mean agreement, disagreement, sentiment or intensity, and the
chamber never infers any of those. Drawing a thicker line for a stronger
objection would be inventing a measurement the transcript does not contain —
and a 3D view is exactly where an invented measurement would be least
questioned, because a diagram looks like data. The caption under the table says
so, in the one place a reader will actually read it.

Addressees are **derived**, not declared: the mandates write prose, not routing
headers, so an edge appears when the CFO's turn contains "the COO". A seat
naming itself produces no edge — a self-loop on a round table is a circle nobody
can read, and it is not an argument between two people. Word boundaries are
enforced, so "cooperative" does not seat the COO.

## Why the seats have no faces

Abstract forms, deliberately. Giving the mandates faces would invite a reader to
trust them as people, and their expertise is prompt-defined. The interface
should not add authority the system does not have.

## Where this could mislead, and what stops it

| Risk | What prevents it |
|---|---|
| A sparse diagram reads as a broken one | The caption states what an edge is, so few edges read as a quiet debate rather than a failed render |
| Glow reads as importance | Glow is **recency only**. A seat that spoke a lot earlier fades like any other; a seat's size never changes |
| Edge thickness reads as strength | Every edge is drawn identically. There is no thickness channel to misread |
| The picture disagrees with the record | It is computed from the record on every load, and there is nowhere else for it to come from |
| The report figure differs from the screen | The report uses the same SVG, drawn from the same numbers |

## The fallback is not a placeholder

The SVG table is what renders under `prefers-reduced-motion` with no WebGL, on a
machine without a GPU, and in print. Same seats, same edges, same numbers.

Progressive enhancement is tested by **denying WebGL** — the test overrides
`getContext` so `webgl` returns `null`, which is the condition a real machine
presents rather than a flag the app sets for itself.

Reduced motion keeps the 3D table where WebGL exists; what it loses is the
pulse, not the view. A reader who dislikes movement has not asked to be shown
less.

## Performance

`frameloop="demand"`. A boardroom table is not a game: the scene renders when a
turn arrives or the replay moves, and at no other time. The only animation is a
slow breath on the emissive intensity of the seat currently speaking, and that
stops under reduced motion.

---

## Measured: do five agents actually argue with each other?

[`docs/results/D1-chamber-edges.json`](results/D1-chamber-edges.json)

**Before any facilitation rule: ten turns, zero edges.** The only seat names in
the whole transcript were self-references — the CMO opening with "**CMO
Argument:**", the COO with "As COO". Not one seat referred to another.

The Test stage rules had said *critique is expected* and *attack arguments,
never the seat making them* — which implies engaging with another seat and never
asks for it. Five agents answering the same question concurrently produce five
position papers filed at once.

**After adding "Name the seat whose argument you are answering": one edge in
ten turns.** A real effect, and a small one. An 8B local model largely does not
engage even when instructed to.

**No further prompt tuning was attempted.** Tuning until the picture looked
busier would be optimising the visualisation rather than the debate, which is
the exact failure this page is written to avoid.

## A colour bug worth recording

The seat colours live in `tokens.css` as `oklch()`, so the margin rail and the
table share one definition. But `getComputedStyle` in this browser returns
`lab(38.1738% 47.3605 28.6629)` — the engine normalises to CIE Lab — and passing
that through a canvas 2D context, the usual normalisation trick, returns `lab()`
as well.

three.js parses neither, so **every seat silently rendered the same grey**, which
looks deliberate. Both colour spaces are parsed now, and the resolved hex is
exposed on the DOM so a test can assert five distinct values rather than five
greys.
