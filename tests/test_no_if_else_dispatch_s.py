"""Owner rule 2026-10-22: no if-else dispatch in the sources.

Guard clauses are allowed: "return early when the input is empty" is not a
branching policy. What is banned is a ladder that decides *which rule applies*:

  * `elif` anywhere in `src` -- a ladder is a table that has not been
    written down yet;
  * `if <expression> == "<literal>"` -- dispatch on a string is a registry that
    has not been written down yet.

Both replacements already exist in the tree and are the models to copy:
`gate.PHYSICAL_RULES`, `gate.FLAG_RULES`, `planners.REMEDY_TRIGGERS`,
`compare.PLANNER_REGISTRY`, `scenarios.THERMAL_PROFILE`.
"""

from __future__ import annotations

import re
from pathlib import Path

SOURCES = Path(__file__).resolve().parents[1] / "src"
ELIF = re.compile(r"^\s*elif\b")
LITERAL_DISPATCH = re.compile(r"^\s*if\b.*==\s*[\"']")


def _python_files():
    return [
        path
        for path in SOURCES.rglob("*.py")
        if "__pycache__" not in path.parts
    ]


def test_no_elif_in_research_sources():
    offences = []
    for path in _python_files():
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if ELIF.match(line):
                offences.append(f"{path.name}:{number}: {line.strip()}")
    assert not offences, "elif ladders found (use a table):\n" + "\n".join(offences)


def test_no_literal_string_dispatch_in_research_sources():
    offences = []
    for path in _python_files():
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if LITERAL_DISPATCH.match(line):
                offences.append(f"{path.name}:{number}: {line.strip()}")
    assert not offences, (
        "literal string dispatch found (use a registry):\n" + "\n".join(offences)
    )
