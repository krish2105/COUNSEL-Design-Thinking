"""Which embedding model can COUNSEL actually use, and where?

COUNSEL retrieves across English, Hindi and Arabic. That is not a nice-to-have:
the record has to hold a citation whatever language the turn was authored in.
So the model is chosen by measurement, and the measurement is this file.

THE TEST. One sentence in three languages, plus an unrelated English control.
A usable model puts the translations far above the control. A model that puts
them below it is not merely weaker — it would rank an unrelated English chunk
ABOVE the correct Arabic one, which is a wrong answer with a citation attached.

THE SECOND CONSTRAINT, discovered while writing this. The deployed instance has
no Ollama, so it embeds in-process with fastembed. Render's free tier gives
512 MB of RAM, which rules out multilingual-e5-large (2.24 GB) regardless of how
well it scores. The deployed model therefore has to be measured under that
ceiling, not chosen from a leaderboard.

Run: uv run python scripts/spike_embeddings.py
"""

from __future__ import annotations

import json
import math
import sys
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "docs/results/A5-embedding-spike.json"
OLLAMA = "http://localhost:11434"

# One claim, three languages, and a control that is unmistakably about something
# else. The control is the whole test: similarity scores mean nothing in the
# abstract, only relative to what an unrelated sentence scores.
PROBE = {
    "en": "The CFO objected that the hypermarket pilot has a longer payback period.",
    "hi": "सीएफओ ने आपत्ति जताई कि हाइपरमार्केट पायलट की भुगतान अवधि लंबी है।",
    "ar": "اعترض المدير المالي على أن تجربة الهايبرماركت لها فترة استرداد أطول.",
}
CONTROL = "The marketing team prefers bright packaging for summer drinks."

#: A model must beat its own control by at least this margin on BOTH
#: cross-lingual pairs to be usable for retrieval.
MARGIN = 0.25


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    return float(dot / (na * nb)) if na and nb else 0.0


def ollama_embed(model: str, texts: list[str]) -> list[list[float]]:
    req = urllib.request.Request(
        f"{OLLAMA}/api/embed",
        data=json.dumps({"model": model, "input": texts}).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        return json.load(resp)["embeddings"]


def fastembed_embed(model: str, texts: list[str]) -> list[list[float]]:
    from fastembed import TextEmbedding

    return [list(v) for v in TextEmbedding(model_name=model).embed(texts)]


def evaluate(label: str, backend: str, model: str, embed) -> dict:
    texts = [PROBE["en"], PROBE["hi"], PROBE["ar"], CONTROL]
    vectors = embed(model, texts)
    en, hi, ar, control = vectors
    # fastembed returns numpy scalars; coerce to Python floats so the report is
    # plain JSON and the comparisons below are plain bools.
    en_hi = float(cosine(en, hi))
    en_ar = float(cosine(en, ar))
    en_control = float(cosine(en, control))
    usable = bool((en_hi - en_control) >= MARGIN and (en_ar - en_control) >= MARGIN)
    return {
        "label": label,
        "backend": backend,
        "model": model,
        "dim": len(en),
        "en_hi": round(en_hi, 4),
        "en_ar": round(en_ar, 4),
        "en_unrelated_control": round(en_control, 4),
        "margin_hi": round(en_hi - en_control, 4),
        "margin_ar": round(en_ar - en_control, 4),
        "usable_for_trilingual_retrieval": usable,
    }


def main() -> int:
    candidates = [
        ("local (Ollama)", "ollama", "bge-m3:567m", ollama_embed),
        ("local control", "ollama", "nomic-embed-text:latest", ollama_embed),
        (
            "deployed (fastembed, must fit 512 MB)",
            "fastembed",
            "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
            fastembed_embed,
        ),
    ]

    rows = []
    for label, backend, model, fn in candidates:
        try:
            rows.append(evaluate(label, backend, model, fn))
        except Exception as exc:  # noqa: BLE001 — a missing model is a result, not a crash
            rows.append(
                {
                    "label": label,
                    "backend": backend,
                    "model": model,
                    "error": f"{type(exc).__name__}: {exc}",
                    "usable_for_trilingual_retrieval": False,
                }
            )

    report = {
        "generated_by": "scripts/spike_embeddings.py",
        "run_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "probe": PROBE,
        "control": CONTROL,
        "required_margin_over_control": MARGIN,
        "candidates": rows,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")

    print(f"{'model':<58}{'dim':>6}{'EN~HI':>8}{'EN~AR':>8}{'ctrl':>8}{'usable':>9}")
    for r in rows:
        if "error" in r:
            print(f"{r['model']:<58}{'':>6}  {r['error'][:44]}")
            continue
        print(
            f"{r['model']:<58}{r['dim']:>6}{r['en_hi']:>8.3f}{r['en_ar']:>8.3f}"
            f"{r['en_unrelated_control']:>8.3f}{str(r['usable_for_trilingual_retrieval']):>9}"
        )
    print(f"\nwritten to {OUT.relative_to(REPO)}")

    by_model = {r["model"]: r for r in rows}
    failures = []
    if not by_model["bge-m3:567m"].get("usable_for_trilingual_retrieval"):
        failures.append("bge-m3 must clear the margin — it is the local embedder")
    if by_model["nomic-embed-text:latest"].get("usable_for_trilingual_retrieval"):
        failures.append(
            "nomic-embed-text unexpectedly cleared the margin; the disqualification "
            "recorded in docs/models.md no longer holds and must be revisited"
        )
    if failures:
        for f in failures:
            print(f"FAILED: {f}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
