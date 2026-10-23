# SW-PKG  -  Package Manifest

| Field | Value |
|---|---|
| Document ID | SW-PKG |
| Kind | Repository document (published) |
| Version | 1.1 |
| Status | Active |
| Date | 2026-10-23 |
| Scope | The exact set of paths that make up the published artefact |
| Enforced by | `tests/test_doc_separation_s.py` |

## 1. Rule

Two kinds of writing live in this repository: repository documents, which describe the artefact
and how to reproduce it, and system records, which are the working record of the programme
(decisions, plans, status, professional material). Only the first kind is published.

This file is the single answer to "what is published". A path is published when it appears in
section 2 and nowhere else. A path that is not listed is not published, even if it is committed.

## 2. Published paths

```
README.md
PACKAGE.md
LICENSE
LICENSE-SPEC
docs/02_TRACK_B_COLDCHAIN.md
docs/03_EVIDENCE_2026.md
docs/05_REPRODUCTION.md
docs/06_EVENT_AGNOSTIC_GATE.md
docs/07_LICENSING.md
docs/08_B4_MEASUREMENT.md
docs/09_CATALYST_LAYER.md
docs/10_NUMERIC_CORE.md
docs/11_PHYSICS_LAYERS.md
docs/12_ROBUSTNESS.md
config/
evidence/
src/switchyard/
scripts/
tests/
pyproject.toml
engine/Cargo.toml
engine/Cargo.lock
engine/src/main.rs
```

## 3. Deliberately not published

| Path | Content | Why not |
|---|---|---|
| `record/`, a folder beside this repository rather than a path inside it | Decision log, programme rules, plans, status, professional material, host-system audit, and the machine registry | Internal record, and outside the artefact by construction: work and paper live in different folders. A decision log invites an argument about the decision instead of the measurement, and professional material is personal |
| `engine/target/` | Cargo build output | Records the host toolchain path; git-ignored |
| `__pycache__/`, `.pytest_cache/` | Interpreter and test caches | Machine state |

## 4. How the boundary is enforced

1. `tests/test_doc_separation_s.py` fails if a published document contains a decision
   identifier, a personal reference, a personal-name class token, or a pointer into the record
   folder. It also fails if the record directory ever appears inside this repository again.
2. The same test fails if a path in section 2 does not exist, if a document under `docs/` is
   missing from section 2, or if a record path appears in it.
3. `tests/test_research_scrub_s.py` fails on a personal name, an e-mail address, a phone
   number, a host path, or a third-party product token anywhere in the tree that git would
   publish. The licence files are the one exemption, because a licence must name its holder:
   the set is exactly `LICENSE` and `LICENSE-SPEC`, it is resolved by path, and a second test
   proves the name appears in no other tracked file.
4. `tests/test_research_project_s.py` fails if a document loses its identification block, its
   ASCII property, or its metadata.

## 5. Release checklist

1. Run the gates in `docs/05_REPRODUCTION.md` section 5.
2. Confirm that section 2 above lists every document under `docs/`, and that no record path
   appears inside this repository at all.
3. Publish the paths in section 2. Do not publish the branch as a whole: it contains the
   internal records by design.
