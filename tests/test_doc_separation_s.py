# -*- coding: utf-8 -*-
"""Gate: repository documents and system records stay separate, and neither leaks (2026-10-23).

Why this gate exists
--------------------
Two kinds of writing had grown together under one directory: documents that describe the
artefact (what it does, what it measured, how a reader reproduces it) and the working
record of the programme (decisions, schedules, professional material, the audit of a
private code base). Mixing them produced three defects at once: a published document
cited `D-19`, which a reader cannot resolve; a schedule was published as if it were
part of the product; and the tree carried a name that pointed back to the publisher.

The split is a directory boundary, not a convention: `_system/` holds the
records, everything else in this repository is published. `PACKAGE.md` lists the
published paths. This file enforces both directions and the absence of the brand.
"""
from __future__ import annotations

import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
RESEARCH = ROOT
SYSTEM = RESEARCH / "_system"

# Tokens that identify the host system, its vocabulary, or the person behind the work.
# A published document must read as a standalone product artefact.
BANNED = {
    "brand_token": re.compile(r"(?i)\bbhr\b|bar h|hawkins|trident"),
    "host_vocabulary": re.compile(
        r"(?i)\bimprint\b|canon_|canon\b|spine_|outline_gates|knowledge_base"
        r"|core/outline|docs/spine_library"
    ),
    "decision_identifier": re.compile(r"\bD-\d{1,2}\b"),
    "system_path": re.compile(r"_system"),
    "owner_register": re.compile(r"(?i)\bowner\b|\bboss\b|\bceo\b|curriculum vitae"),
    "undecided_handover": re.compile(r"(?i)outstanding items|approved for execution|pending owner"),
}


def published_documents() -> list:
    return [RESEARCH / "README.md", RESEARCH / "PACKAGE.md"] + sorted(
        (RESEARCH / "docs").glob("*.md")
    )


def system_records() -> list:
    return sorted(path for path in SYSTEM.rglob("*.md") if path.is_file())


def read(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def test_no_brand_or_host_reference_in_a_published_document():
    # PACKAGE.md has one job that needs the internal path: it names what is not published.
    allowance = {("PACKAGE.md", "system_path")}
    offenders = []
    for path in published_documents():
        for number, line in enumerate(read(path).splitlines(), 1):
            for label, pattern in BANNED.items():
                match = pattern.search(line)
                if match and (path.name, label) not in allowance:
                    offenders.append(
                        f"{path.relative_to(ROOT).as_posix()}:{number}:{label}:{match.group(0)[:40]}"
                    )
    assert offenders == [], "internal reference in a published document:\n" + "\n".join(offenders[:20])


def _tree_text_files() -> list:
    suffixes = {".md", ".py", ".json", ".rs", ".toml", ".txt", ".csv", ".yaml", ".yml"}
    skip = {"target", "__pycache__", ".venv", "node_modules", ".pytest_cache"}
    instrument = pathlib.Path(__file__).resolve()
    found = []
    for path in RESEARCH.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in suffixes:
            continue
        if skip & set(path.relative_to(RESEARCH).parts):
            continue
        # A pattern table has to contain the tokens it searches for. This module is the
        # definition of the gate, not content that ships as content, so it is exempt; the
        # exemption is one file and it is stated here rather than inferred from a name.
        if path.resolve() == instrument:
            continue
        found.append(path)
    return sorted(found)


def test_no_brand_token_anywhere_in_the_tree():
    """The boundary is the whole tree, not only the documents: a record is still shipped
    with the repository, and a brand token in one is a token that points back."""
    pattern = BANNED["brand_token"]
    offenders = []
    for path in _tree_text_files():
        for number, line in enumerate(read(path).splitlines(), 1):
            match = pattern.search(line)
            if match:
                offenders.append(
                    f"{path.relative_to(ROOT).as_posix()}:{number}:{match.group(0)[:40]}"
                )
    assert offenders == [], "host brand token inside the tree:\n" + "\n".join(offenders[:20])


def test_every_published_document_declares_that_it_is_published():
    for path in published_documents():
        text = read(path)
        head = text.splitlines()[0]
        body = "\n".join(text.splitlines()[:12])
        assert head.startswith("# SW-"), (path.name, head)
        assert "| Kind | Repository document" in body, path.name
        assert "Document ID" in body and "Status" in body and "Version" in body, path.name


def test_every_system_record_declares_that_it_is_internal():
    records = system_records()
    assert records, "the system record directory must exist and hold the working record"
    for path in records:
        body = "\n".join(read(path).splitlines()[:12])
        assert "| Kind | System record" in body, path.name
        assert "internal" in body.lower(), path.name


def test_a_system_record_is_never_referenced_by_a_published_document():
    """Match full relative paths: a bare file name such as README.md is not a pointer."""
    pointers = {
        path.relative_to(RESEARCH).as_posix() for path in system_records()
    } | {"_system/README.md", "_system/programme.json"}
    offenders = []
    for path in published_documents():
        text = read(path)
        for pointer in pointers:
            if pointer in text:
                offenders.append(f"{path.name} -> {pointer}")
    assert offenders == [], f"published documents point at internal records: {offenders}"

def _manifest_paths() -> list:
    text = read(RESEARCH / "PACKAGE.md")
    block = text.split("## 2. Published paths", 1)[1].split("## 3.", 1)[0]
    return [line.strip() for line in block.splitlines() if line.strip() and not line.strip().startswith("```")]


def test_package_manifest_is_complete_and_publishable():
    listed = _manifest_paths()
    assert listed, "PACKAGE.md must list the published paths"
    for entry in listed:
        assert (ROOT / entry.rstrip("/")).exists(), f"manifest lists a missing path: {entry}"
        assert "_system" not in entry, f"manifest must not publish an internal record: {entry}"
    published = {path.relative_to(ROOT).as_posix() for path in published_documents()}
    missing = published - set(listed)
    assert missing == set(), f"documents missing from the manifest: {sorted(missing)}"


def test_decision_log_mirrors_the_machine_record():
    programme = json.loads(read(SYSTEM / "programme.json"))
    log = read(SYSTEM / "DECISIONS.md")
    missing = [entry["id"] for entry in programme["decisions"] if entry["id"] not in log]
    assert missing == [], f"decisions in programme.json but absent from DECISIONS.md: {missing}"


def test_no_record_is_left_under_config_or_docs():
    """The registry used to live in `config/` and the plans and audit in `docs/`."""
    assert not (RESEARCH / "config" / "research_projects.json").exists()
    assert not (RESEARCH / "docs" / "00_CAPABILITY_AUDIT.md").exists()
    assert not (RESEARCH / "docs" / "01_TRACK_A_SILICON.md").exists()
    assert not (RESEARCH / "docs" / "04_ASSET_INVENTORY.md").exists()
    assert not (RESEARCH / "docs" / "05_PLAN_5_DAYS.md").exists()
    assert not (RESEARCH / "docs" / "05_PLAN_35_DAYS.md").exists()


def test_the_gate_would_catch_a_leaking_line():
    """A gate that cannot fail is not a gate: prove each pattern fires."""
    sample = (
        "| D-19 | bar H ranch | SW-11 | the owner approved | imprint | "
        "core/outline/x.py | see _system/DECISIONS.md | outstanding items |"
    )
    hits = {label for label, pattern in BANNED.items() if pattern.search(sample)}
    assert hits == set(BANNED), f"patterns that did not fire: {set(BANNED) - hits}"
