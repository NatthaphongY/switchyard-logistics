# SW-SYS-07 - Delivery plan (5 to 7 days), as executed

| Field | Value |
|---|---|
| Document ID | SW-SYS-07 |
| Kind | System record (internal; not published) |
| Version | 3.1 |
| Status | Closed; the plan was executed |
| Date | 2026-10-22 |
| Licence | Apache-2.0 |

Supersedes the 35-day plan. That plan was written before the capability audit was
finished and before any code existed; it priced work that turned out to be one
afternoon each. This plan is the one that was executed, with the real file paths
and the real evidence files.

Rule: a day is only "done" when a command in this document reproduces the result
from a clean checkout. No day is done because it looks done.

## Day 1 - Capability audit and separation

- Audit: `docs/00_CAPABILITY_AUDIT.md` (4 confirmed, 2 label-only, 1 degenerate,
  2 unsupported). Nothing was claimed that the audit did not confirm.
- Worktree isolation: branch `eda-coldchain`, separate directory.
- Decision record opened in `config/research_projects.json`.

## Day 2 - Event-agnostic gate

- `src/switchyard/model.py` - immutable records, canonical hash.
- `src/switchyard/gate.py` - 20 codes, four as data tables.
- `docs/06_EVENT_AGNOSTIC_GATE.md` v1.0 (normative). No named event appears in
  any decision path; the word "cold chain" appears only in prose.

## Day 3 - Planners and the composition rule

- `src/switchyard/planners.py` - three planners: current practice,
  generation one, generation two.
- Composition: the baseline is always a candidate, so the shipped plan can never
  be worse than practice under the gate's own ordering.
- `src/switchyard/scenarios.py` - seeded generator, six event axes.

## Day 4 - Physical layers

- `src/switchyard/physics.py` - queueing, traffic flow, heat transfer,
  reaction kinetics, reliability, epidemic final size, expected shortfall.
- `config/physics.json` - every constant, as data.
- `docs/11_PHYSICS_LAYERS.md` - what was adopted, what was rejected, and why.

## Day 5 - Numeric core and conformance

- `engine/src/main.rs` - replay core, integer decisions only.
- `scripts/export_instances.py` - 300 instances, full precision.
- Result: 300 checks, 0 mismatches. Throughput and memory in
  `evidence/STRESS.md`.

## Day 6 - Measurement and pre-registered criteria

- `scripts/run_b4.py --scenarios 300` (headline) and the same command
  with `--ablation --tag ABL` (section 4 of the measurement note)
- `evidence/B4_MEASUREMENT_V2.json` and `.md`, plus `..._WX.*` for the ambient
  layer and `..._ABL.*` for the ablation, so no run overwrites another
- Six criteria fixed before the run, including two guards that can fail the
  result (thermal non-inferiority, delivered quantity).

## Day 7 - Robustness, documentation, release pack

- `scripts/stress_parity.py --repeats 200` -> `evidence/STRESS.md`
- Licensing: `docs/07_LICENSING.md`, change date set to two years.
- Public surface carries the product name Switchyard (D-21, 2026-10-23) after a
  prior-art check; the registry id `SW` stays as the document and gate
  identifier, so no evidence file was renamed.

## Repeatable test log

Every run below was executed on this machine; the numbers are copied from the
evidence files, not from memory.

| Command | Expected | Evidence |
|---|---|---|
| `py -3.13 -m pytest tests -q` | green | test summary in the commit |
| `py -3.13 -X utf8 scripts/export_instances.py --scenarios 300` | 300 instances written | `evidence/instances.txt` |
| `switchyard-core --instances evidence/instances.txt --threads 8 --repeat 200` | 0 mismatches | `evidence/STRESS.json` |
| `py -3.13 -X utf8 scripts/stress_parity.py --repeats 200` | PASS | `evidence/STRESS.md` |
| `py -3.13 -X utf8 scripts/run_b4.py --scenarios 300` | SEPARATES | `evidence/B4_MEASUREMENT_V2.md` |
| `... run_b4.py --scenarios 300 --weather --tag WX` | SEPARATES, 0.0223/0.0126/0.0112 p(any) | `evidence/B4_MEASUREMENT_V2_WX.md` |
| `... run_b4.py --scenarios 300 --weather --weather-profile synthetic --tag WXS` | replays the pre-2026-10-23 numbers, 0.0224/0.0127/0.0112 p(any) | `evidence/B4_MEASUREMENT_V2_WXS.md` |
| `... run_b4.py --scenarios 300 --ablation --tag ABL` | SEPARATES | `evidence/B4_MEASUREMENT_V2_ABL.md` |

## Feature notes (what is deliberately not built)

| Not built | Why | Re-open when |
|---|---|---|
| Planner in Rust | The planner is 12.9 s for 300 cases in Python; parity is cheap to keep because the decision function is small. Porting it would double the surface that must stay bit-identical. | A consumer needs sub-second planning |
| Compute-shader gate | ~1e-4 accuracy, no true 64-bit integers, so it cannot be used for a release-time hash | Never, for this artefact |
| Learned model anywhere | The claim is determinism and replay, not prediction | A labelled data set exists |
| External domain reviewer | No budget (D-1); limitations stated instead of hidden | A reviewer volunteers |
| Named product | Decided 2026-10-23: Switchyard (D-21). Prior art checked: the name exists on the Python Package Index as an unrelated networking framework, so a distribution would need a suffix. | Owner reopens if the name collides commercially |

## Standing rule for future work

Any new rule goes in as a row in a table (`PHYSICAL_RULES`, `FLAG_RULES`,
`REMEDY_TRIGGERS`, `PLANNER_REGISTRY`), never as a new branch. Two guard tests
enforce this: `tests/test_no_if_else_dispatch_s.py` and
`tests/test_ascii_only_s.py`.
