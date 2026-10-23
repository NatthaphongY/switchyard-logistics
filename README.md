# SW-README  -  switchyard-logistics

| Field | Value |
|---|---|
| Document ID | SW-README |
| Kind | Repository document (published) |
| Version | 3.2 |
| Status | Active |
| Date | 2026-10-23 |
| Product name | switchyard-logistics. Document and gate identifiers are `SW-xx`; the import package is `switchyard` and the binary is `switchyard-core`. |
| Repository | Standalone. Extracted from the host tree on 2026-10-23; the host keeps no copy |
| Audience | Repository maintainers, external reviewers, prospective contributors |
| Normative status | Informative; SW-06 is the normative specification |

## 1. Purpose and scope

This programme asks whether the optimisation and verification machinery of a private
production-planning code base transfers to industrial planning problems, and whether the
result can be packaged as a verifiable public artefact.

The question is answered by building the artefact and measuring it: an event-agnostic
compliance gate for time-and-temperature critical plans, a Python reference implementation, a
dependency-free Rust replay core, and a pre-registered measurement of whether a priced plan
separates from current practice under the gate's own ordering.

Two workstreams were assessed. Workstream B (logistics) is active. Workstream A
(semiconductor floorplanning) is suspended and unstaffed; it is not part of this release.

## 2. Document set

| ID | Document | Content |
|---|---|---|
| SW-02 | `docs/02_TRACK_B_COLDCHAIN.md` | Problem statement, capability gap, architecture |
| SW-03 | `docs/03_EVIDENCE_2026.md` | Evidence register: market and technical sources with retrieval dates |
| SW-05 | `docs/05_REPRODUCTION.md` | Reproduction and verification: every number, and the command that regenerates it |
| SW-06 | `docs/06_EVENT_AGNOSTIC_GATE.md` | Specification of the compliance gate (normative) |
| SW-07 | `docs/07_LICENSING.md` | Licensing model, thresholds, and legal position |
| SW-08 | `docs/08_B4_MEASUREMENT.md` | Gate B4 measurement, escalation ladder, and the verdict as measured |
| SW-09 | `docs/09_CATALYST_LAYER.md` | Propagation, information, institutional and catalyst layers; cascade model |
| SW-10 | `docs/10_NUMERIC_CORE.md` | Fixed-point arithmetic, Rust conformance core, measured throughput |
| SW-11 | `docs/11_PHYSICS_LAYERS.md` | Queueing, traffic, thermal, reliability and epidemic layers: adopted, rejected, limits |
| SW-12 | `docs/12_ROBUSTNESS.md` | Bit-exact parity over repeated passes, hostile input, liveness and memory evidence |
| SW-PKG | `PACKAGE.md` | What is published, and what is deliberately not |

The normative document is SW-06. Where any other document conflicts with it, SW-06 governs.

## 3. Properties of the artefact

These properties are binding on the released artefact. Each is enforced by code or by a test,
not by convention.

1. Two licences with different purposes: the specification is Apache-2.0 in `LICENSE-SPEC`, so it
   can be cited and independently implemented; the reference implementation is Business Source
   Licence 1.1 in `LICENSE`, with an Additional Use Grant and a published Change Date; the names
   and marks are not licensed (SW-07).
2. The gate is event-agnostic. Decision logic reads state and constraints; a named event never
   appears in a branch, a table key, or a threshold (SW-06 section 3).
3. All decisions use integer micro-units and integer minutes. Floating point is confined to
   transport and reporting (SW-10).
4. Two implementations exist: the Python reference and a dependency-free Rust core. Conformance
   is proved by replaying exported instances, not by inspection: 300 of 300 agree, bit for bit
   (SW-10, SW-12).
5. The measurement was pre-registered. The escalation ladder, the two guard criteria, and the
   decision rule were fixed before the run, and both limbs of every criterion are reported even
   when only one is met (SW-08).
6. Only openly licensed data is used, and no data is purchased. Ambient conditions come from a
   frozen July 1991-2020 ERA5 climatology retrieved from a free, keyless archive API, with
   attribution stored inside the data file (SW-11).
7. Rules are tables, not branches: a new code is a row in `PHYSICAL_RULES`, `FLAG_RULES`,
   `REMEDY_TRIGGERS` or `PLANNER_REGISTRY`. Text is English and ASCII, and both rules have a
   test.

## 4. Constraints

The following constraints apply to all work in this programme.

1. The programme MUST NOT write to the host production tree.
2. Every quantitative claim MUST cite a source and a retrieval date, or a source location in
   the form `path:line`, or a command whose output is reproducible.
3. A failed gate MUST stop the associated workstream. Thresholds MUST NOT be lowered to
   achieve a pass.
4. Language models MUST NOT be used for tasks that can be completed deterministically by code
   or by hand.
5. No artefact may be produced that has no caller, consumer, or documented purpose.
6. All text in this repository MUST be written in English.
7. Content MUST be free of decorative notation. Emoji and similar markers are not permitted in
   documents; status is expressed in words.
## 5. Language and style policy

The artefact is published openly and is expected to be read by an international audience.

- Documents use professional English and the normative keywords of RFC 2119 (MUST, MUST NOT,
  SHOULD, SHOULD NOT, MAY).
- Status is expressed as explicit terms: `Confirmed`, `Label-only`, `Degenerate`, `Unsupported`,
  `Suspended`, `Active`.
- Literals in other scripts that are required as evidence MUST be written as escape sequences
  so that files remain ASCII.
- Style and language rules are enforced by the test suite, not by convention; see section 7.

## 6. Repository separation

The programme is a standalone repository:

```
git rev-parse --show-toplevel
# <repository-root>
```

Host paths are omitted on purpose: the document is published, the machine layout is not part
of the evidence. The tree was extracted from the host repository on 2026-10-23. It is not a
worktree of the host and shares no branch with it.

The earlier work is carried as ancestry rather than as a copy: the commit under which the
programme lived in the host repository is reachable from this branch through a root commit whose
tree is that commit's `research/` subtree, with the original author, date and message. A reader
can therefore read the first commit of the programme without visiting the host repository, and
`git log --graph` shows where the two lines join:

```
git log --graph --oneline
# *   the extracted state on top of the graft
# |\
# | * the programme as it stood inside the host repository
# * the extracted state
```


Working rules:

1. Commits are made by the repository maintainer. Contributors do not commit.
2. The host production tree MUST NOT contain a copy of this repository. If one appears, it is
   a defect.
3. Nothing here modifies production source files. Re-entry into production goes through a
   proposal, a maintainer decision, and an implementation with tests.

## 7. Verification

| Check | Command | Expected |
|---|---|---|
| Programme test suite | `py -3.13 -m pytest tests/test_research_project_s.py tests/test_coldchain_engine_s.py tests/test_physics_layers_s.py tests/test_physical_gate_s.py tests/test_stats_s.py -q` | all tests pass |
| Ambient data | `py -3.13 -m pytest tests/test_weather_regions_s.py -q` | integers only, provenance present, the measured table differs from the invented one |
| Publication scrub | `py -3.13 -m pytest tests/test_research_scrub_s.py -q` | no e-mail, phone number, host path, personal name or third-party token in the published tree |
| Document separation | `py -3.13 -m pytest tests/test_doc_separation_s.py -q` | published documents carry no internal record, no decision identifier, and no host-system reference |
| Rule guards | `py -3.13 -m pytest tests/test_no_if_else_dispatch_s.py tests/test_ascii_only_s.py -q` | no elif, no literal dispatch, ASCII only |
| Rust conformance | `switchyard-core --instances evidence/instances.txt --threads 8 --repeat 200` | 0 mismatches |
| Robustness | `py -3.13 -X utf8 scripts/stress_parity.py --repeats 200` | PASS |
| Document set | section 2 of this document, and `PACKAGE.md` | all documents exist and are published |

## 8. Reproduction of the evidence

`docs/05_REPRODUCTION.md` is the single place where every published number is tied to the
command that produces it and to the evidence file that stores the output. The short form:

```powershell
py -3.13 -X utf8 scripts/export_instances.py --scenarios 300
py -3.13 -X utf8 scripts/run_b4.py --scenarios 300
py -3.13 -X utf8 scripts/stress_parity.py --repeats 200
```

## 9. Current status

| Item | Status |
|---|---|
| Capability audit | Complete; the findings that survive are the ones implemented here |
| Evidence register | Complete for the sources used; limitations recorded in SW-03 section 4 |
| Gate specification | Normative v1.1, 20 codes (SW-06) |
| Gate implementation | Complete: Python reference, three planners, integer rules (SW-06, SW-10) |
| Physical layers | Complete: queue, traffic, thermal, reliability, epidemic, tail risk (SW-11) |
| Numeric core | Complete: 300 checks, 0 mismatches, 34,011 per second on eight threads (SW-10) |
| Robustness | Complete: 200 passes, no mismatches, six hostile inputs bounded (SW-12) |
| Gate B4 | **SEPARATES** on six pre-registered criteria (SW-08) |
| Ambient data | Measured: ERA5 July 1991-2020 climatology via the free Open-Meteo archive API, three sites (SW-11) |
| Public release | Not prepared. The product name is decided and prior art has been checked; the release pack is not built |

## 10. Known limitations

1. No external domain reviewer. The limitations are recorded in SW-03 section 4, SW-11
   section 11, and SW-12, rather than reviewed away.
2. The ambient layer is a frozen July climatology, not a live forecast ingest, and it covers
   three sites rather than the whole year (SW-11).
3. Heat gain per consignment is drawn from a distribution, not measured, and the cascade
   calibration is synthetic (SW-09, SW-11). The claim is determinism and replay, not prediction.
4. Throughput is measured on one machine, with the numbers and thread count stated in SW-10.
5. The complete repository test suite is not green on this machine for reasons unrelated to
   this programme; the commands in section 7 are the ones that must pass.
