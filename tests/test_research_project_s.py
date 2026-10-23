# -*- coding: utf-8 -*-
"""Gate: programme registry + the honest-audit verdict (2026-10-23).

Why this gate exists
--------------------
The owner asked whether a third-party AI proposal over-claimed the capability of
this repository. The audit answered "partly": three mechanisms are genuine
(Edmonds-Karp min-cut, critical-path slack, causal DAG ordering) and three are
not what their names suggest. Without a gate, the marketing wording can quietly
drift back and the downgraded claims would be lost.

These tests therefore pin (a) the registry shape, (b) the verdict itself, and
(c) the *measured* behaviour that produced the verdict - so a future change that
actually implements sheaf cohomology or a real transit state machine will fail
here and force the audit to be updated instead of silently diverging.
"""
from __future__ import annotations

import hashlib
import json
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
# The programme registry is a record, not part of the artefact: since 2026-10-23 it lives in
# the `record` folder beside this repository, so this tree holds work and published
# documents only. A published clone has no record folder, and the registry gates skip there
# rather than fail on a file that was never published.
RECORD = ROOT.parent / "record"
REG = RECORD / "programme.json"
DOCS = ROOT / "docs"

# The published document set. The records that used to sit beside these (capability audit,
# suspended workstream A, asset inventory, both plans) are now outside the repository, in the
# `record` folder beside it: they are the working record of the programme, not part of the
# artefact. `_system/` was their name inside the tree until the split on 2026-10-23.
REQUIRED_DOCS = (
    "02_TRACK_B_COLDCHAIN.md",
    "03_EVIDENCE_2026.md",
    "05_REPRODUCTION.md",
    "06_EVENT_AGNOSTIC_GATE.md",
    "07_LICENSING.md",
    "08_B4_MEASUREMENT.md",
    "09_CATALYST_LAYER.md",
    "10_NUMERIC_CORE.md",
    "11_PHYSICS_LAYERS.md",
    "12_ROBUSTNESS.md",
)


def _reg() -> dict:
    if not REG.is_file():
        pytest.skip("the programme registry is not beside this repository (record folder absent)")
    return json.loads(REG.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# registry shape
# ---------------------------------------------------------------------------

def test_registry_parses_with_two_tracks_and_a_paused_eda():
    d = _reg()
    assert [t["id"] for t in d["tracks"]] == ["B", "A"]      # logistics first (owner 2026-10-23)
    assert d["tracks"][0]["status"] == "active"
    assert d["tracks"][1]["status"] == "paused_by_owner"
    assert all(t["gates"] for t in d["tracks"])


def test_every_gate_has_deliverable_and_pass_rule():
    for track in _reg()["tracks"]:
        for gate in track["gates"]:
            assert gate.get("deliverable"), gate
            assert gate.get("pass"), gate
            assert "kill" in gate, gate


def test_write_scope_is_repository_wide_and_gates_fail_closed():
    rules = _reg()["_rules"]
    assert rules["write_scope"] == "repository/**"
    assert rules["read_only_paths"] == []   # the host tree is no longer reachable
    assert rules["no_llm_for_small_tasks"] is True
    assert rules["fail_closed"]


def test_probabilities_are_ranges_not_single_numbers():
    for track in _reg()["tracks"]:
        for key, val in track["my_probability"].items():
            assert isinstance(val, list) and len(val) == 2, f"{track['id']}:{key}"
            lo, hi = val
            assert 0.0 <= lo <= hi <= 1.0, f"{track['id']}:{key}"
        # the prior claim is retained for comparison, never used as the plan
        assert 0.0 < track["prior_claim_probability"] < 1.0


# ---------------------------------------------------------------------------
# the verdict itself
# ---------------------------------------------------------------------------

def test_verdict_keeps_downgraded_claims_downgraded():
    v = _reg()["verdict_of_prior_claims"]
    assert "edmonds_karp_min_cut" in v["confirmed"]
    assert "critical_path_method" in v["confirmed"]
    assert "cellular_sheaf_cohomology" in v["label_only"]
    assert "non_equilibrium_thermo_speed_limit" in v["degenerate_or_mislabeled"]
    assert "three_phase_transit_state_machine" in v["degenerate_or_mislabeled"]


def test_required_documents_exist_and_are_substantive():
    for name in REQUIRED_DOCS:
        p = DOCS / name
        assert p.is_file(), name
        assert p.stat().st_size > 800, f"{name} is too small to be evidence"


# ---------------------------------------------------------------------------
# owner direction 2026-10-23: event-agnostic, BSL split, English-only
# ---------------------------------------------------------------------------

def test_event_model_is_agnostic_and_named_events_stay_out_of_logic():
    ev = _reg()["event_agnostic"]
    assert len(ev["axes"]) == 6, "six axes: onset, notice, duration, magnitude, scope, reversibility"
    assert len(ev["damage_patterns"]) >= 6
    assert len(ev["unsafe_control_actions"]) >= 6
    assert ev["banned_in_logic"], "the ban list must be explicit"
    allowed = " ".join(ev["named_events_allowed_only_in"])
    assert "scenarios" in allowed, "named events may appear as sample data only"
    for pattern in ev["banned_in_logic"]:
        assert isinstance(pattern, str) and pattern.strip()


def test_licensing_is_split_between_free_spec_and_bsl_reference():
    lic = _reg()["licensing"]
    comps = {c["name"]: c for c in lic["components"]}
    assert comps["gate-spec"]["license"] == "Apache-2.0"
    assert comps["gate-ref"]["license"] == "BSL-1.1"
    assert comps["gate-ref"]["additional_use_grant"]
    assert lic["never"], "the licence must state what it does not guarantee"


def test_bsl_grant_has_verifiable_thresholds_and_a_change_date():
    ref = {c["name"]: c for c in _reg()["licensing"]["components"]}["gate-ref"]
    grant = ref["additional_use_grant"]
    free_for = " ".join(grant["production_use_free_for"]).lower()
    assert "usd 5m" in free_for and "100 employees" in free_for, (
        "the free tier must be revenue + headcount (verifiable), never fleet size"
    )
    assert grant["everything_else"] == "commercial licence required"
    assert any("hosted service" in x.lower() for x in grant["excluded"])
    assert ref["change_license"] == "Apache-2.0"
    assert ref["change_date_years"] in (2, 4), "BSL caps the change date at four years"


def _licence_digest(path: pathlib.Path) -> str:
    """Digest of the licence text with line endings normalised to LF.

    Git stores these files with LF and may check them out with CRLF on Windows, so the raw
    bytes differ between machines while the text does not. Normalising keeps the recorded
    digest meaningful on both, and still catches a change of wording.
    """
    text = path.read_bytes().decode("utf-8").replace("\r\n", "\n")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def test_the_licence_files_carry_the_recorded_terms_and_their_digests():
    """A licence is legal text: it changes by decision, and the record holds its digest.

    The two files are the only place in this tree where a personal name is allowed, so the
    terms in them are pinned here rather than trusted to stay in step with the registry.
    The digest check is the honest half: editing the wording without recording it fails.
    """
    code = (ROOT / "LICENSE").read_text(encoding="utf-8")
    spec = (ROOT / "LICENSE-SPEC").read_text(encoding="utf-8")
    assert code.startswith("Business Source License 1.1")
    assert "Licensor:" in code, "BUSL-1.1 requires the licensor to be specified"
    assert "Change License:       Apache License, Version 2.0" in code
    assert "Change Date:          2028-10-23" in code, "two years from first distribution (D-15)"
    assert "USD 5 million" in code and "fewer than 100" in code, (
        "the grant in the text and the threshold in the registry must be the same sentence"
    )
    ref = {c["name"]: c for c in _reg()["licensing"]["components"]}["gate-ref"]
    assert ref["change_date_years"] == 2, "D-15 fixes two years; four is the legal ceiling"
    assert spec.lstrip().startswith("Apache License")
    assert "Version 2.0, January 2004" in spec, "the specification licence is the Apache text"
    files = _reg()["licensing"]["files"]
    assert set(files) == {"code", "specification"}
    for entry in files.values():
        path = ROOT / entry["path"]
        assert path.is_file(), entry["path"]
        assert _licence_digest(path) == entry["sha256"], (
            f"{entry['path']} changed without the registry being updated"
        )


def test_licensing_records_the_clean_room_reality_and_label_rules():
    lic = _reg()["licensing"]
    stance = lic["clean_room_stance"]
    assert "expression" in stance["legal_fact"] and "idea" in stance["legal_fact"]
    assert stance["patent"], "a patent grant/retaliation clause must be recorded"
    assert any("conformance" in x for x in stance["therefore"])
    assert any("not 'open source'" in n or "open source" in n for n in lic["never"]), (
        "a BSL release must never be advertised as OSI open source"
    )
    names = [a["name"] for a in lic["alternatives_considered"]]
    assert any("PolyForm Small Business" in n for n in names)


def test_goal_is_reputation_first_and_data_is_open_only():
    d = _reg()
    assert d["goal"]["primary"] == "reputation_portfolio"
    assert "revenue" in d["goal"]["secondary"]
    answers = [x["answer"] for x in d["resolved_owner_decisions"]]
    assert any("$0" in a and "open data" in a for a in answers)


def test_import_back_policy_blocks_direct_edits_to_production():
    pol = _reg()["import_back_policy"]
    assert any(p.startswith("core/outline") for p in pol["forbidden_direct_edit"])
    assert "owner approval" in pol["rule"]


def test_research_is_english_only():
    """Open source: a reader on the internet cannot read Thai.

    Any character in the Thai block (U+0E00-U+0E7F) anywhere in the repository fails this
    gate - including inside JSON values - so the public project stays English.
    """
    offenders = []
    for path in (ROOT).rglob("*"):
        if not path.is_file() or path.suffix.lower() not in {".md", ".json", ".txt", ".py"}:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        thai = [c for c in text if 0x0E00 <= ord(c) <= 0x0E7F]
        if thai:
            offenders.append((path.relative_to(ROOT).as_posix(), len(thai)))
    assert offenders == [], f"Thai characters in the repository (must be English): {offenders}"


# Symbols that mark a document as informal rather than technical.
_DECORATIVE_RANGES = (
    (0x1F000, 0x1FAFF),   # pictographs, emoji, transport, symbols
    (0x2300, 0x23FF),     # technical symbols used as status marks
    (0x2600, 0x27BF),     # misc symbols and dingbats
    (0x2B00, 0x2BFF),     # arrows and stars used as status marks
    (0xFE0F, 0xFE0F),     # variation selector, keeps emoji presentation
)
_INFORMAL_TOKENS = ("CEO", "Boss", "lol", "haha")


def _documents():
    return [ROOT / "README.md"] + sorted(DOCS.glob("*.md"))


def test_documents_contain_no_decorative_markers():
    """A technical specification states status in words, not in symbols."""
    offenders = []
    for path in _documents():
        text = path.read_text(encoding="utf-8")
        for char in text:
            code = ord(char)
            if any(lo <= code <= hi for lo, hi in _DECORATIVE_RANGES):
                offenders.append(f"{path.name}:U+{code:04X}")
                break
    assert offenders == [], f"decorative markers in documents: {offenders}"


def test_documents_avoid_informal_register():
    offenders = []
    for path in _documents():
        text = path.read_text(encoding="utf-8")
        for token in _INFORMAL_TOKENS:
            if token in text:
                offenders.append(f"{path.name}:{token}")
    assert offenders == [], f"informal markers in documents: {offenders}"


def test_documents_are_ascii_only():
    """Portability: the public document set is ASCII, so it renders identically everywhere."""
    offenders = []
    for path in _documents():
        text = path.read_text(encoding="utf-8")
        for char in text:
            if ord(char) > 127:
                offenders.append(f"{path.name}:U+{ord(char):04X}")
                break
    assert offenders == [], f"non-ASCII characters in documents: {offenders}"


def test_documents_carry_identification_metadata():
    """Every document declares its identifier, version, and status."""
    for path in _documents():
        text = path.read_text(encoding="utf-8")
        head = text.splitlines()[0]
        assert head.startswith("# SW-"), (path.name, head)
        body = "\n".join(text.splitlines()[:12])
        assert "Document ID" in body, path.name
        assert "Status" in body, path.name
        assert "Version" in body, path.name
        assert "Kind" in body, path.name


def test_superseded_plans_are_system_records_not_documents():
    """A schedule is a working record: it describes a team, not the artefact."""
    assert (DOCS / "05_REPRODUCTION.md").is_file()
    assert not (DOCS / "05_PLAN_5_DAYS.md").exists()
    assert not (DOCS / "05_PLAN_35_DAYS.md").exists()
    plans = RECORD / "plans"
    if not plans.is_dir():
        pytest.skip("the record folder is not beside this repository")
    assert (plans / "PLAN_5_DAYS.md").is_file()
    assert (plans / "PLAN_35_DAYS_superseded.md").is_file()
    for track in _reg()["tracks"]:
        for phase in track.get("phases", []):
            assert phase["days"] and phase["out"], phase


def test_product_name_is_recorded_with_its_prior_art():
    """The name is a decision, not a preference (owner, 2026-10-23).

    The owner settled the name twice on the same day: `Switchyard` first (D-21), then
    `switchyard-logistics` (D-24), because the bare name is taken on the Python Package
    Index. Both decisions stay in the record, the older one marked as superseded, and the
    identifiers are pinned so that a rename never renumbers documents or moves an import.
    """
    d = _reg()
    name = d["product_name"]
    assert name["name"] == "switchyard-logistics"
    assert name["decided"] == "2026-10-23"
    assert "D-21" in name["previous"] and "superseded" in name["previous"]
    assert name["prior_art"], "a chosen name must carry the prior-art check"
    assert any("Package Index" in entry["what"] for entry in name["prior_art"]), (
        "the distribution-name collision is the one that matters if anything is published"
    )
    decisions = {entry["id"]: entry for entry in d["decisions"]}
    assert {"D-21", "D-24"} <= set(decisions)
    rename = decisions["D-24"]["decision"]
    assert "switchyard-core" in rename and "SW-xx" in rename, (
        "the rename must say which names are identifiers and therefore do not move"
    )
    decision = next(x for x in d["open_owner_decisions"] if x["id"] == name["decision"])
    assert decision["status"] == "resolved"
    assert decision["options"] == ["Switchyard"]
    assert "SW" in decision["resolution"], "document identifiers stay stable"
    assert "switchyard-logistics" in decision["resolution"], (
        "the resolution must carry the name that is in force, not only the first choice"
    )


def test_forbidden_claims_do_not_reach_a_published_document():
    """A claim the measurement does not support is listed once and then gated.

    The list lives in the programme record, because it is a decision about what may
    be said; the gate lives here, because the published documents are what a reader
    sees. Without it the wording reappears the first time somebody writes a summary.
    """
    claims = _reg().get("forbidden_claims") or []
    assert claims, "the programme record must list the claims the measurement does not support"
    published = [ROOT / "README.md", ROOT / "PACKAGE.md"] + sorted(
        DOCS.glob("*.md")
    )
    offenders = []
    for entry in claims:
        phrase = entry["phrase"]
        for path in published:
            if phrase.lower() in path.read_text(encoding="utf-8").lower():
                offenders.append(f"{path.name}: {phrase}")
    assert offenders == [], f"forbidden claim in a published document: {offenders}"


def test_no_document_still_asks_for_a_product_name():
    """Once decided, no document may describe the name as pending."""
    stale = []
    for path in [ROOT / "README.md"] + sorted(DOCS.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        if "owner is choosing the name" in text or "pending owner naming" in text:
            stale.append(path.name)
    assert stale == [], f"documents still describe the name as undecided: {stale}"
