# SW-SYS-00 - System record index (internal)

| Field | Value |
|---|---|
| Document ID | SW-SYS-00 |
| Kind | System record (internal; not published) |
| Version | 1.0 |
| Status | Active |
| Date | 2026-10-23 |

## 1. Why this directory exists

Two kinds of writing had been mixed in `docs/`:

- repository documents: what the artefact does, what it measured, how a reader reproduces
  it;
- system records: decisions, schedules, professional material, and the state of the work.

A published tree cannot carry the second kind. A decision log invites an argument about a
decision instead of the measurement, a schedule describes a team rather than a product, and
professional material is personal by definition. Mixing them also produced dangling
references: a published document cited `D-19`, and a reader without the decision log has no
way to resolve it.

The split is a directory boundary, not a convention:

| Kind | Paths | Published |
|---|---|---|
| Repository documents | `README.md`, `PACKAGE.md`, `docs/`, `evidence/` | Yes |
| System records | `_system/` | No |

`tests/test_doc_separation_s.py` enforces the boundary in both directions, and
`PACKAGE.md` lists what is published so the question has one answer.

## 2. Contents

| File | Content |
|---|---|
| `DECISIONS.md` | Decision log: `D-1` to `D-22`, the questions they answer, product-name prior art, and the business context |
| `programme.json` | Machine record: rules, decisions, the two workstreams with their gates and probabilities, licensing record, import-back policy, verdict on the prior claims |
| `PROFESSIONAL_MATERIAL.md` | Professional material: verified claims for external communication, and the rule that it is not published |
| `STATUS.md` | State of the work, open items, and known blockers |
| `FUTURE_PROJECTS.md` | Work recorded for later: separating the tree from the host, removing duplication, and the three candidate projects |
| `HOST_SYSTEM_AUDIT.md` | Capability audit of the host system, with file and line numbers |
| `HOST_ASSET_INVENTORY.md` | Reusable assets of the host system, measured from disk |
| `TRACK_A_EDA.md` | Suspended workstream A, kept so the suspension has a record |
| `plans/PLAN_5_DAYS.md` | The plan that was executed, as an internal execution record |
| `plans/PLAN_35_DAYS_superseded.md` | The withdrawn plan, kept as history |

## 3. Rules

1. A published document states the consequence of a decision, never the decision entry and
   never its identifier.
2. Nothing in this directory is referenced from `README.md`, `PACKAGE.md` or `docs/`.
3. English, ASCII, no decorative markers. The repository-wide gates apply here as well:
   `tests/test_research_project_s.py`.
4. A decision is appended to `programme.json` and mirrored in `DECISIONS.md`. The mirror is
   checked by a test, so the two cannot drift.
5. A question that is still open is recorded with its options. An open question is not a
   blocker for work that does not depend on it.
