"""The OWASP scorecard, generated from the tests rather than written beside them.

WHY IT IS GENERATED
-------------------
A mapping table in a document is a claim. This one is assembled by reading the
test suite: a risk is marked covered only if a test named for it exists, and a
risk with no test is printed as a GAP rather than quietly omitted.

That inverts the usual failure. A hand-written scorecard drifts — a control is
described, the test that backed it is deleted or renamed in a refactor, and the
document keeps asserting coverage that no longer exists. Here the document
cannot say more than the suite does.

Two risks are marked NOT APPLICABLE with a reason. That is also deliberate:
silently dropping them from the table would look like an oversight, and an
unenforced control that looks enforced is worse than an admitted gap.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

TESTS = Path(__file__).resolve().parents[3] / "tests/invariants/test_owasp.py"


@dataclass(frozen=True)
class Risk:
    id: str
    title: str
    control: str
    #: Set when the risk cannot apply to this system, with the reason.
    not_applicable: str | None = None


RISKS: tuple[Risk, ...] = (
    Risk(
        "LLM01",
        "Prompt injection",
        "One untrusted-content boundary. Uploaded documents and search results are "
        "scanned and fenced; a poisoned document is ingested and marked rather than "
        "refused, and cannot change the memo.",
    ),
    Risk(
        "LLM02",
        "Insecure output handling",
        "Nothing a model returns is executed. Memo claims must pass require_citations, "
        "and structured output is schema-validated before it is used.",
    ),
    Risk(
        "LLM03",
        "Training data poisoning",
        "",
        not_applicable=(
            "COUNSEL trains nothing. It calls hosted or local models and stores no "
            "weights, so there is no training corpus to poison. Model provenance is "
            "recorded in docs/models.md instead."
        ),
    ),
    Risk(
        "LLM04",
        "Model denial of service",
        "Request-count quotas per provider, a 180-token cap per turn, a bounded "
        "prompt that stops growing with the debate, and a kill switch checked before "
        "any provider is consulted.",
    ),
    Risk(
        "LLM05",
        "Supply chain vulnerabilities",
        "Dependencies pinned by uv.lock and package-lock.json. Every model is named "
        "with its licence in docs/models.md, and every data source with its licence "
        "and retrieval date in docs/datasets.md.",
    ),
    Risk(
        "LLM06",
        "Sensitive information disclosure",
        "Prompt-exfiltration attempts are flagged at the boundary. Secrets are read "
        "from the environment and never placed in a prompt. RBAC gates every write.",
    ),
    Risk(
        "LLM07",
        "Insecure plugin design",
        "A declarative capability registry. Every tool declares side_effects and a "
        "test asserts False across the whole registry; a grant naming a tool that "
        "does not exist fails the suite.",
    ),
    Risk(
        "LLM08",
        "Excessive agency",
        "No agent holds a tool that acts on the world. The five mandates hold search "
        "and ask; only the Facilitator can open or close a round.",
    ),
    Risk(
        "LLM09",
        "Overreliance",
        "Claims that fail the citation gate are quarantined and labelled rather than "
        "dropped. A recommendation every seat dissents from is flagged on the memo's "
        "face. Brier scores are withheld below five outcomes.",
    ),
    Risk(
        "LLM10",
        "Model theft",
        "",
        not_applicable=(
            "COUNSEL holds no proprietary weights. The local models are publicly "
            "downloadable and the hosted ones are the providers' own."
        ),
    ),
)

_TEST_ID = re.compile(r"def (test_(LLM\d\d)_[a-z0-9_]+)\(", re.I)


def covering_tests() -> dict[str, list[str]]:
    """Which tests claim to cover which risk, read from the suite itself."""
    if not TESTS.exists():
        return {}
    found: dict[str, list[str]] = {}
    for name, risk in _TEST_ID.findall(TESTS.read_text(encoding="utf-8")):
        found.setdefault(risk.upper(), []).append(name)
    return found


def scorecard() -> dict[str, object]:
    tests = covering_tests()
    rows = []
    gaps = []
    for risk in RISKS:
        names = tests.get(risk.id, [])
        if risk.not_applicable:
            status = "not applicable"
        elif names:
            status = "covered"
        else:
            status = "GAP"
            gaps.append(risk.id)
        rows.append(
            {
                "id": risk.id,
                "title": risk.title,
                "status": status,
                "control": risk.control or risk.not_applicable,
                "tests": sorted(names),
            }
        )
    covered = [r for r in rows if r["status"] == "covered"]
    return {
        "generated_by": "services/api/security/scorecard.py, read from tests/invariants/test_owasp.py",
        "note": (
            "Generated from the test suite, not written beside it. A risk is covered "
            "only if a test named for it exists; a risk with no test prints as a GAP. "
            "The document cannot claim more than the suite proves."
        ),
        "risks": rows,
        "n_covered": len(covered),
        "n_not_applicable": sum(1 for r in rows if r["status"] == "not applicable"),
        "n_gaps": len(gaps),
        "gaps": gaps,
        "n_assertions": sum(len(r["tests"]) for r in rows),
    }
