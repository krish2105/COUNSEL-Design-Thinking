
# COUNSEL — 15 viva questions, with answers

Answers are grounded in what was measured, including the failures. Where a
number appears it is read from docs/results/.

---

**1. Why bounded, side-effect-free agents?**
Because prompting cannot keep that promise. "Do not post anything" is a request,
and an injected instruction is a competing request. COUNSEL keeps it by there
being nothing to call: every tool declares `side_effects` and a test asserts
`False` across the whole registry. The live attack asks for `publish_memo`; that
tool does not exist.

**2. How are citations enforced?**
Retrieval-then-verify. Candidate spans come from the corpus, and a claim only
survives if it shares a verbatim phrase of 24+ characters with the span it
cites. The quote is read back out of the database and compared. A test asserts
that a sentence about penguins does not acquire a citation merely by ranking
near one.

**3. What does the Auditor actually catch?**
Four mechanical rules: fabricated source, unsupported number, ad-hominem, and
stage-rule breach. Recall 1 with a 0
false-positive rate on 42 seeded cases, and
5 of 5 on held-out turns.

**4. That seeded number looks too good. Is it?**
Yes, and the script says so. I wrote the corpus and the rules together, so it
measures internal consistency more than generalisation. The held-out run against
real model turns is the honest one — and it found a bug the seeded corpus never
would: hedging was judged per turn, so "If conversion drops below 12%…"
immunised a later "the plant has a proven 15% conversion rate".

**5. What does the Auditor miss?**
A confident, well-hedged, entirely wrong argument with no numbers in it. It
checks the *form* of an argument — sourcing, target, stage discipline — not its
truth. Truth is the room's job and the ledger's.

**6. Where could the 3D view mislead?**
Three ways, all closed. Glow is recency, not importance, so a seat that spoke a
lot earlier fades. Every edge is drawn identically, so there is no thickness
channel to misread as intensity. And an edge means one seat *named* another —
not that it agreed — which the caption says under the picture.

**7. Why do so few edges appear?**
Because the seats barely engage. Ten turns produced 0
cross-references; the only seat names were self-references. A facilitation rule
moved it to 1. I stopped tuning there: making the picture
busier would have been optimising the visualisation rather than the debate.

**8. What did the free-tier constraint force you to do better?**
Four things. A provider abstraction rather than an SDK call, so which vendor
serves a turn is not structural. A deterministic stub that is the CI substrate,
so the entire suite runs with no model. Request-count quotas, because a token
budget I cannot verify is theatre. And a bounded prompt — the thing that took a
three-round debate from 126.5s to 60.9s.

**9. Why is Anthropic in the chain if it is disabled?**
Because an absence reads as an oversight and invites someone to fill it. A
refusal with a test behind it is a stated position: the test sets the API key and
asserts the provider stays unselectable.

**10. Your embedding choice — defend it.**
Measured, not chosen from a leaderboard. bge-m3 puts a Hindi translation at
0.8302 against an unrelated control at 0.4626.
nomic-embed-text puts it at 0.3364 against
0.4356 — *below* its own control, so it would rank an unrelated
English chunk above the correct Arabic one and cite it. Disqualified, not
deprioritised.

**11. Your memo recommended something every agent disagreed with. Explain.**
The scores gave hypermarket 55 to plant's
51 — a margin of 4 across five seats and three
axes, inside the noise. The prose round said what 1–5 integer scoring was too
coarse to express. The memo now carries that contradiction above the ranking
table; a recommendation nobody supports should not be published under an
authoritative-looking number.

**12. Is the transcript really tamper-proof?**
No — tamper-*evident*. The signing key sits beside the data, so anyone who can
edit the database can re-sign a forged chain. It catches corruption, partial
writes, and any edit made through or around the application, which is what a
hash chain buys. Resisting a determined operator needs the key held where the
application cannot read it, and that is a deployment decision.

**13. What is the counterfactual actually doing?**
Arithmetic over recorded positions. Remove an evidence id, drop the scores that
cited it, re-aggregate. It answers *how much of this decision rests on that
source*, not *what would the room decide without it* — a real re-debate might
land elsewhere. Every surface that shows a flip says so.

**14. When does the Brier score mean anything?**
Not yet. It is withheld below five outcomes and the seats show as pending with
how many more they need. A score across two sessions is noise wearing a decimal
point, and a caller that defaulted it to zero would show a perfectly calibrated
seat that has never been tested.

**15. What would this need to become a product?**
Real identities behind the RBAC roles; the signing key held outside the
application; durable storage for the ledger; and enough logged outcomes for
calibration to mean anything. None of those change the architecture — they move
where the trust boundary sits.
