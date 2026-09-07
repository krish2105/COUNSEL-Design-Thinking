"""The report may not print a number that no measurement supports.

The weak way to honour "every figure traces to docs/results/" is to look the
numbers up while writing and paste them in — true on the day, quietly false a
week later when a re-measurement moves a value. These tests pin the strong
version: the template holds keys, the values are read at build time, and a
missing results file breaks the build rather than emitting a stale figure.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from services.api.reports.figures import BY_KEY, FIGURES, MissingFigure, figure

REPO = Path(__file__).resolve().parents[2]
RESULTS = REPO / "docs/results"


def _template() -> str:
    """The template constant, not the whole file.

    Scanning the source caught a placeholder written inside a comment, which is
    documentation rather than a figure.
    """
    import importlib.util

    spec = importlib.util.spec_from_file_location("build_report", REPO / "scripts/build_report.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.TEMPLATE


def test_every_figure_in_the_template_is_declared():
    keys = set(re.findall(r"\{\{([a-z0-9_.]+)\}\}", _template()))
    assert keys, "the template should contain figure placeholders"
    undeclared = keys - set(BY_KEY)
    assert undeclared == set(), f"template uses undeclared figures: {undeclared}"


def test_no_figure_is_declared_and_then_unused():
    """A registry with entries nothing uses is a registry nobody checks."""
    keys = set(re.findall(r"\{\{([a-z0-9_.]+)\}\}", _template()))
    unused = set(BY_KEY) - keys
    assert unused == set(), f"declared but never printed: {unused}"


@pytest.mark.parametrize("fig", FIGURES, ids=[f.key for f in FIGURES])
def test_every_declared_figure_resolves_today(fig):
    assert fig.rendered() != ""


def test_a_missing_results_file_fails_the_build_rather_than_printing_a_stale_number(tmp_path):
    """Deleting a measurement must break the report. If it did not, the document
    would keep asserting a number nothing supports."""
    from services.api.reports import figures as mod

    original = mod.RESULTS
    try:
        mod.RESULTS = tmp_path  # an empty results directory
        with pytest.raises(MissingFigure, match="does not exist"):
            mod.BY_KEY["auditor.recall"].value()
    finally:
        mod.RESULTS = original


def test_an_undeclared_key_raises_rather_than_rendering_empty():
    with pytest.raises(MissingFigure, match="no figure declared"):
        figure("auditor.invented_metric")


def test_the_built_report_contains_no_unsubstituted_placeholders():
    md = REPO / "docs/artefacts/MGT204_MAJLIS_report.md"
    if not md.exists():
        pytest.skip("report not built yet; run scripts/build_report.py")
    text = md.read_text()
    assert "{{" not in text and "}}" not in text
    for banned in ("TBD", "TODO", "lorem ipsum"):
        assert banned not in text


def test_the_report_carries_its_limitations_and_its_failures():
    """A report that only lists what worked is marketing. These are the sections
    an examiner should be able to find."""
    md = REPO / "docs/artefacts/MGT204_MAJLIS_report.md"
    if not md.exists():
        pytest.skip("report not built yet")
    text = md.read_text()
    for required in (
        "Honest limitations",
        "prompt-defined",
        "did not stop the fabrication",
        "not robust",
        "rewards copying",
    ):
        assert required in text, f"the report omits: {required}"


def test_every_results_file_the_figures_need_exists():
    needed = {f.file for f in FIGURES}
    missing = {f for f in needed if not (RESULTS / f).exists()}
    assert missing == set(), missing


def test_results_files_are_valid_json():
    for path in RESULTS.glob("*.json"):
        json.loads(path.read_text())


# ── the other three artefacts ───────────────────────────────────────────────

ARTEFACTS = ("MGT204_deck_outline.md", "MGT204_viva_15.md", "MGT204_demo_3min.md")


def _artefact_templates():
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "build_artefacts", REPO / "scripts/build_artefacts.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return {"deck": module.DECK, "viva": module.VIVA, "demo": module.DEMO}


def test_the_deck_and_viva_cite_only_declared_figures():
    """One registry across every artefact, so a slide cannot quote a number the
    report contradicts."""
    for name, template in _artefact_templates().items():
        keys = set(re.findall(r"\{\{([a-z0-9_.]+)\}\}", template))
        undeclared = keys - set(BY_KEY)
        assert undeclared == set(), f"{name} uses undeclared figures: {undeclared}"


@pytest.mark.parametrize("name", ARTEFACTS)
def test_every_artefact_is_built_and_fully_substituted(name):
    path = REPO / "docs/artefacts" / name
    if not path.exists():
        pytest.skip("artefacts not built; run scripts/build_artefacts.py")
    text = path.read_text()
    assert "{{" not in text and "}}" not in text
    for banned in ("TBD", "TODO", "lorem ipsum"):
        assert banned not in text


def test_the_viva_answers_the_hard_questions_not_only_the_flattering_ones():
    """A viva sheet that only rehearses what worked is a liability in the room."""
    path = REPO / "docs/artefacts/MGT204_viva_15.md"
    if not path.exists():
        pytest.skip("artefacts not built")
    text = path.read_text()
    for required in (
        "That seeded number looks too good",
        "What does the Auditor miss",
        "Where could the 3D view mislead",
        "Is the transcript really tamper-proof",
        "tamper-*evident*",
        "every agent disagreed",
    ):
        assert required in text, f"the viva sheet dodges: {required}"


def test_the_demo_script_has_a_fallback_for_a_cold_model():
    path = REPO / "docs/artefacts/MGT204_demo_3min.md"
    if not path.exists():
        pytest.skip("artefacts not built")
    text = path.read_text()
    assert "If the model is cold" in text
    assert "If nothing works" in text, "a demo script without a failure plan is optimism"
