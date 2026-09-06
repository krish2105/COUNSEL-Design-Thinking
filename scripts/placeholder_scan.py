"""Placeholder gate.

A generated report that still says TBD is worse than no report: it looks
finished. This scan is wired into `make check` so the tree cannot reach a
phase gate carrying an unfilled hole.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

# Directories whose content is authored by this project and must be complete.
SCAN_DIRS = ["docs", "services", "apps/web/app", "apps/web/components", "apps/web/lib"]
SCAN_FILES = ["README.md"]

# The plan documents legitimately quote the master plan's own phase language and
# describe the scan itself, so they are excluded from their own gate.
EXCLUDE = re.compile(r"(docs/superpowers/plans/|node_modules/|\.next/|__pycache__/)")

PATTERNS = {
    "TBD": re.compile(r"\bTBD\b"),
    "TODO": re.compile(r"\bTODO\b"),
    "FIXME": re.compile(r"\bFIXME\b"),
    "lorem ipsum": re.compile(r"\blorem ipsum\b", re.I),
    "XXX": re.compile(r"\bXXX\b"),
    "angle-bracket placeholder": re.compile(r"<(placeholder|your[- ]|insert )", re.I),
}

SUFFIXES = {".md", ".py", ".ts", ".tsx", ".css", ".json", ".yml", ".yaml"}


def scan() -> list[str]:
    hits: list[str] = []
    targets: list[Path] = [REPO / f for f in SCAN_FILES]
    for d in SCAN_DIRS:
        targets.extend(p for p in (REPO / d).rglob("*") if p.is_file())

    for path in targets:
        if not path.exists() or path.suffix not in SUFFIXES:
            continue
        rel = path.relative_to(REPO).as_posix()
        if EXCLUDE.search(rel):
            continue
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            for name, pattern in PATTERNS.items():
                if pattern.search(line):
                    hits.append(f"{rel}:{lineno}: {name}: {line.strip()[:90]}")
    return hits


def main() -> int:
    hits = scan()
    if hits:
        print(f"placeholder scan FAILED — {len(hits)} hit(s):", file=sys.stderr)
        for h in hits:
            print(f"  {h}", file=sys.stderr)
        return 1
    print("placeholder scan clean")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
