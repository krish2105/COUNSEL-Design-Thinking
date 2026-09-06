# Claude Code kickoff prompts (one per repo; paste the block for the project you're starting)

Common preamble (include in each):

> You are building <PROJECT> from scratch for my SP Jain MAIB Term 4 course <CODE>, portfolio and job search. Read `docs/superpowers/plans/2026-09-06-term4-master-plans-v2.md`, section <N>, in full, plus the shared header. For patterns only — never imports — you may read ~/Desktop/MAIB-Term4/RAQIB-AI-in-Operations and ~/Desktop/MAIB-Term4/YIELDMAP (Control-Room tokens, LLMProvider, crew runtime, memory guard, OWASP harness, Term 4 doc builders). This repo is standalone.
>
> Execute end to end: superpowers:writing-plans to expand the master plan into a task-level plan with interfaces and tests, then superpowers:executing-plans, inline, no subagents, Phases A → E.
>
> Rules that override everything: (1) zero paid inference — `LLMProvider` with Ollama → Gemini free → Groq free, Anthropic present but off; quotas as request counts; degrade gracefully; you choose the embedding model after a spike and record it in `docs/models.md`. (2) Only free, licensed data; every source in `docs/datasets.md` with URL, date, licence; if a source is inaccessible, use the named fallback and say so. (3) Every number traceable to `docs/results/`; every factual sentence in any generated report cited; no agent has side-effect tools beyond what the plan lists; nothing is ever published or executed externally. (4) Tests green per task, one conventional commit per task with the Claude co-author trailer; don't ask me per task. (5) Stop only at phase ends (tell me what to click on the live URLs), secrets or Supabase/Render/Vercel/GitHub actions, or decisions that cost money or change a safety/"not advice" boundary. (6) After each phase: deploy, update README Live section and `docs/results/`, placeholder scan, 5-line summary.
>
> Start now: create the repo, run `ollama list`, verify every data source with a sample fetch, list assumptions about models, quotas and 3D data, print the Phase A task plan with one verifiable check per task, and wait for my "go".

---

## COUNSEL (build second, after YIELDMAP)
Fill: `<PROJECT>` = COUNSEL, `<CODE>` = MGT 204 Design Thinking, `<N>` = 3, repo `COUNSEL-Design-Thinking`.
Add: "Demo decision for the presentation: 'Should RAQIB pilot in a Dubai hypermarket or a Greenlam plant first?' Use it as the seeded example session. Search backend: try SearXNG in Docker first; if it fails in 20 minutes, fall back to user-supplied links and note it."

## UPLIFT (build third)
Fill: `<PROJECT>` = UPLIFT, `<CODE>` = AI 208 AI in Marketing, `<N>` = 1, repo `UPLIFT-AI-in-Marketing`.
Add: "Footfall/demand series comes from RAQIB's seeded simulator export (label `simulated=true` everywhere it appears). If the Dubai events feed is not machine-readable, build the curated 24-month events CSV from public listings and label it curated. No agent posts anything anywhere; publishing is a human export."

## AUTHENTIC8 (build fourth)
Fill: `<PROJECT>` = AUTHENTIC8, `<CODE>` = AI 219 Ethics, Sociology & Governance of AI, `<N>` = 2, repo `AUTHENTIC8-AI-in-Governance`.
Add: "Defensive only: never generate synthetic media, never write evasion or attack guidance, store no biometric templates, delete uploads per the retention job. Choose 2–3 open-weight, permissively licensed detectors and record them in `docs/models.md`; if an eval set needs a request form, print instructions and exit rather than downloading. Every report needs a calibration section, a bias section and a reviewer sign-off before export."
