# BHR-RS-README  -  Research Programme Overview

| Field | Value |
|---|---|
| Document ID | BHR-RS-README |
| Version | 2.3 |
| Status | Approved for execution |
| Date | 2026-10-23 |
| Product name | Switchyard (decision D-21). Document and gate identifiers stay `BHR-RS-xx`. |
| Branch | `research/eda-coldchain` (isolated Git worktree) |
| Audience | Repository maintainers, external reviewers, prospective contributors |
| Normative status | Informative; the decisions in section 3 are binding |

## 1. Purpose and scope

This programme evaluates whether the optimisation and verification machinery of the
Bar H Ranch Publishing System transfers to industrial planning problems, and whether it
can be packaged as a verifiable public artefact.

The programme is organisationally and technically separate from the book production
pipeline. It reads production data but never writes to it. All work is conducted on the
git branch `research/eda-coldchain`, checked out in a dedicated worktree.

Two workstreams were assessed:

| ID | Workstream | Status |
|---|---|---|
| B | Time-and-temperature critical plans: event-agnostic compliance gate | Active |
| A | Semiconductor floorplanning and routing (EDA) | Suspended by decision D-4 |

## 2. Document set

| ID | Document | Content |
|---|---|---|
| BHR-RS-00 | `docs/00_CAPABILITY_AUDIT.md` | Capability findings, each supported by source location or executed result |
| BHR-RS-01 | `docs/01_TRACK_A_SILICON.md` | Assessment of the suspended EDA workstream |
| BHR-RS-02 | `docs/02_TRACK_B_COLDCHAIN.md` | Active workstream: problem statement, gap analysis, architecture |
| BHR-RS-03 | `docs/03_EVIDENCE_2026.md` | Evidence register: market and technical sources with retrieval dates |
| BHR-RS-04 | `docs/04_ASSET_INVENTORY.md` | Reusable assets, measured from disk |
| BHR-RS-05 | `docs/05_PLAN_5_DAYS.md` | Execution plan (5-7 days), gates, and termination criteria |
| BHR-RS-06 | `docs/06_EVENT_AGNOSTIC_GATE.md` | Specification of the compliance gate (normative) |
| BHR-RS-07 | `docs/07_LICENSING.md` | Licensing model, thresholds, and legal position |
| BHR-RS-08 | `docs/08_B4_MEASUREMENT.md` | Gate B4 measurement, escalation ladder, and the verdict as measured |
| BHR-RS-09 | `docs/09_CATALYST_LAYER.md` | Propagation, information, institutional and catalyst layers; cascade model |
| BHR-RS-10 | `docs/10_NUMERIC_CORE.md` | Fixed-point arithmetic, Rust conformance core, measured throughput |
| BHR-RS-11 | `docs/11_PHYSICS_LAYERS.md` | Queueing, traffic, thermal, reliability and epidemic layers: adopted, rejected, limits |
| BHR-RS-12 | `docs/12_ROBUSTNESS.md` | Bit-exact parity over repeated passes, hostile input, liveness and memory evidence |

The normative document is BHR-RS-06. Where any other document conflicts with it, BHR-RS-06
governs.

## 3. Recorded decisions

Decisions are dated and treated as fixed inputs until formally revised.

| ID | Decision | Date |
|---|---|---|
| D-1 | No external investment. No return-on-investment defence is required. | 2026-10-23 |
| D-2 | Licensing uses the Business Source Licence 1.1 with an Additional Use Grant, paired with a specification published under Apache-2.0. | 2026-10-23 |
| D-3 | Elaborate mathematical machinery is permitted within this programme but is prohibited on the book production path. Re-import requires evidence. | 2026-10-23 |
| D-4 | Logistics is the active workstream. EDA is suspended and is not staffed. | 2026-10-23 |
| D-5 | The event model MUST be event-agnostic. Named events MUST NOT appear in decision logic. | 2026-10-23 |
| D-6 | Data acquisition budget is zero. Only openly licensed data is used. | 2026-10-23 |
| D-7 | The primary objective is professional reputation and a verifiable public artefact. Revenue is a secondary consequence. | 2026-10-23 |
| D-8 | The 35-working-day schedule is withdrawn; see D-18. | 2026-10-22 |
| D-15 | Licence change date is two years from first release. Four years remains the legal maximum. | 2026-10-22 |
| D-16 | A non-separating B4 result may ship as a plan auditor, with the limitation stated first. | 2026-10-22 |
| D-17 | No external domain reviewer; limitations are recorded in BHR-RS-03, -11 and -12. | 2026-10-22 |
| D-18 | Schedule re-baselined to five to seven working days. | 2026-10-22 |
| D-19 | A physical layer is adopted only when it changes a decision; constants live in `config/physics.json`. | 2026-10-22 |
| D-20 | The research tree is English and code only, and contains no if/elif dispatch. Both are enforced by tests. | 2026-10-22 |
| D-21 | The product name is Switchyard. Prior art was checked before adoption: the name is already used by an unrelated educational networking framework on the Python Package Index, so a Python distribution would need a suffix. | 2026-10-23 |
| D-22 | Ambient weather data is open reanalysis only: the free, keyless Open-Meteo archive API serving ERA5, frozen as a July 1991-2020 climatology in `config/weather_regions.json`. A live forecast ingest is out of scope until a consumer needs one. | 2026-10-23 |

## 5. Language and style policy

The programme is published openly and is expected to be read by parties who do not read
Thai. Consequently:

- Documents use professional English and the normative keywords of RFC 2119
  (MUST, MUST NOT, SHOULD, SHOULD NOT, MAY).
- Status is expressed as explicit terms: `Confirmed`, `Label-only`, `Degenerate`,
  `Unsupported`, `Suspended`, `Active`.
- Literals in other scripts that are required as evidence MUST be written as escape
  sequences so that files remain ASCII.
- Style and language rules are enforced by the test suite, not by convention; see
  section 7.

## 6. Repository separation

The programme occupies its own branch and its own worktree:

```
git worktree list
# <publisher-checkout>     [master]
# <research-checkout>      [research/eda-coldchain]
```

Host paths are omitted on purpose: the document is published, the machine layout
is not part of the evidence.

Working rules:

1. Commits on this branch are made by the repository lead. Contributors do not commit.
2. The production working tree MUST NOT contain a `research/` directory. If one appears,
   it is a defect.
3. Changes on this branch MUST NOT modify production source files without an approved
   proposal and a corresponding test.

## 7. Verification

| Check | Command | Expected |
|---|---|---|
| Programme test suite | `py -3.13 -m pytest tests/test_research_project_s.py tests/test_coldchain_engine_s.py tests/test_physics_layers_s.py tests/test_physical_gate_s.py tests/test_stats_s.py -q` | all tests pass |
| Rule guards | `py -3.13 -m pytest tests/test_no_if_else_dispatch_s.py tests/test_ascii_only_s.py -q` | no elif, no literal dispatch, ASCII only |
| Ambient data | `py -3.13 -m pytest tests/test_weather_regions_s.py -q` | integers only, provenance present, the measured table differs from the invented one |
| Publication scrub | `py -3.13 -m pytest tests/test_research_scrub_s.py -q` | no e-mail, phone number, host path, personal name or third-party token in the publishable tree |
| Registry integrity | `py -3.13 -X utf8 -c "import json,pathlib;json.loads(pathlib.Path('research/config/research_projects.json').read_text(encoding='utf-8'))"` | exits 0 |
| Document set | section 2 of this document | all documents exist |
| Rust conformance | `bhr-core --instances research/evidence/instances.txt --threads 8 --repeat 200` | 0 mismatches |
| Robustness | `py -3.13 -X utf8 research/scripts/stress_parity.py --repeats 200` | PASS |
| Language and style | included in the test suite | no non-ASCII bytes, no decorative markers |

## 8. Reproduction of the evidence

```powershell
# Capability findings
py -3.13 -m pytest tests/test_true_graph_engines_s.py -q

# Market and technical evidence register
py -3.13 -X utf8 scripts/web_research.py search "cold chain logistics pharma 2026" --limit 8
py -3.13 -X utf8 scripts/web_research.py read "https://www.mordorintelligence.com/industry-reports/cold-chain-logistics-market" --chars 2200
```

## 9. Current status

| Item | Status |
|---|---|
| Capability audit | Complete: four findings confirmed, two label-only, one degenerate, two unsupported |
| Evidence register | Complete for the sources used; limitations recorded in BHR-RS-03 section 4 |
| Asset inventory | Complete |
| Gate specification | Normative v1.1, 20 codes (BHR-RS-06) |
| Gate implementation | Complete: Python reference, three planners, integer rules (BHR-RS-06, BHR-RS-10) |
| Physical layers | Complete: queue, traffic, thermal, reliability, epidemic, tail risk (BHR-RS-11) |
| Numeric core | Complete: 300 checks, 0 mismatches, 34,011 per second on eight threads (BHR-RS-10) |
| Robustness | Complete: 200 passes, no mismatches, six hostile inputs bounded (BHR-RS-12) |
| Gate B4 | **SEPARATES** on six pre-registered criteria (BHR-RS-08) |
| Ambient data | Measured: ERA5 July 1991-2020 climatology via the free Open-Meteo archive API, three sites (D-22) |
| Public release | Not started; the product name is decided (D-21: Switchyard), the release pack is not |

## 10. Outstanding items

1. Business Source Licence change date - **resolved** (D-15: two years).
2. Non-separating result at gate B4 - **resolved** (D-16: may ship as a plan auditor);
   in this run the gate separates, so the fallback is unused.
3. Domain reviewer - **resolved** (D-17: not appointed, limitations documented).
4. Product name - **resolved** (D-21: Switchyard, decided 2026-10-23 after a prior-art
   check); registry id `BHR-RS` remains the document and gate identifier.

## 4. Constraints

The following constraints apply to all work in this programme.

1. The programme MUST NOT write to `projects/**`, `knowledge_base/**`, or `docs/spine_library/**`.
2. Every quantitative claim MUST cite a source and a retrieval date, or a source location
   in the form `path:line`, or a command whose output is reproducible.
3. A failed gate MUST stop the associated workstream. Thresholds MUST NOT be lowered to
   achieve a pass.
4. Language models MUST NOT be used for tasks that can be completed deterministically by
   code or by hand.
5. No artefact may be produced that has no caller, consumer, or documented purpose.
6. All text under `research/**` MUST be written in English. This is a public artefact; see
   section 5.
7. Content MUST be free of decorative notation. Emoji and similar markers are not
   permitted in documents; status is expressed in words.
