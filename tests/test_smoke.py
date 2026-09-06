def test_package_imports():
    import services.api

    assert services.api.__version__


def test_the_placeholder_gate_runs_inside_the_test_suite():
    """The scan is part of `make check`, but wiring it into pytest too means a
    contributor running only the tests still cannot leave a TBD in the docs."""
    import subprocess
    import sys
    from pathlib import Path

    repo = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, str(repo / "scripts/placeholder_scan.py")],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_every_number_cited_in_the_docs_has_a_results_file():
    """docs/ may only cite figures that a script regenerated."""
    from pathlib import Path

    results = Path(__file__).resolve().parents[1] / "docs/results"
    expected = {
        "A2-contrast.json",
        "A4-search-smoke.json",
        "A5-embedding-spike.json",
        "A7-fusion-crosslingual.json",
    }
    present = {p.name for p in results.glob("*.json")}
    assert expected <= present, f"missing results files: {sorted(expected - present)}"
