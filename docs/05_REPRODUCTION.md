# SW-05  -  Reproduction and Verification

| Field | Value |
|---|---|
| Document ID | SW-05 |
| Kind | Repository document (published) |
| Version | 1.0 |
| Status | Active |
| Date | 2026-10-23 |
| Licence | Apache-2.0 |
| Normative status | Informative; SW-06 governs the specification |

## 1. What this document is for

Every number in the published documents is produced by a command in section 3 and stored in a
file under `evidence/`. A number that cannot be reproduced this way is a defect. A number that
is not in `evidence/` is not claimed.

## 2. Environment

| Item | Requirement |
|---|---|
| Python | 3.13, standard library only, no third-party packages |
| Rust | stable toolchain, for the conformance core |
| Network | not required, except for the optional ambient-table rebuild in section 3: the ambient table is committed as a frozen July 1991-2020 climatology, so a measurement run calls no API |
| Credentials | none |
| Machine | any; the numbers below were produced on one machine and the throughput in particular is machine-dependent |

## 3. Commands

| Purpose | Command | Expected | Evidence |
|---|---|---|---|
| Export replay instances | `py -3.13 -X utf8 scripts/export_instances.py --scenarios 300` | 300 instances written | `evidence/instances.txt` |
| Rust conformance | `switchyard-core --instances evidence/instances.txt --threads 8 --repeat 200` | 0 mismatches | `evidence/STRESS.json` |
| Determinism and parity | `py -3.13 -X utf8 scripts/stress_parity.py --repeats 200` | PASS | `evidence/STRESS.md` |
| Gate B4, headline | `py -3.13 -X utf8 scripts/run_b4.py --scenarios 300` | SEPARATES | `evidence/B4_MEASUREMENT_V2.md` |
| Gate B4, ambient layer on | `... run_b4.py --scenarios 300 --weather --tag WX` | SEPARATES | `evidence/B4_MEASUREMENT_V2_WX.md` |
| Gate B4, replay of the pre-change numbers | `... run_b4.py --scenarios 300 --weather --weather-profile synthetic --tag WXS` | reproduces `B4_MEASUREMENT_V2` to within the ambient perturbation | `evidence/B4_MEASUREMENT_V2_WXS.md` |
| Gate B4, ablation | `... run_b4.py --scenarios 300 --ablation --tag ABL` | SEPARATES, identical to the headline | `evidence/B4_MEASUREMENT_V2_ABL.md` |
| Ambient table rebuild (optional, needs network) | `py -3.13 -X utf8 scripts/build_weather_regions.py --dry-run` | prints the derivation without writing; the committed table is the output of the same command without `--dry-run` | `evidence/B4_MEASUREMENT_V2_WX.md` provenance section |

## 4. Expected numbers

All runs use seed 20261023, 300 paired scenarios, intensity 1.0.

| Artefact | Unsafe actions per scenario | Thermal dose per delivered unit (permille) | Verdict |
|---|---|---|---|
| Headline, ambient layer off | 13.2167 / 11.6867 / 5.4000 | 14.2936 / 6.3089 / 3.9335 | SEPARATES |
| Ambient layer on, measured regions | 13.2167 / 11.6867 / 5.4033 | 18.0608 / 7.9721 / 5.0753 | SEPARATES |
| Ambient layer on, synthetic regions | 13.2167 / 11.6867 / 5.4033 | 17.9588 / 8.0293 / 5.1016 | SEPARATES |

Order in each cell: current practice / generation one / generation two.

With the ambient layer on, the exceedance probability is reported per plan class:
0.0223, 0.0126, 0.0112 for measured regions, and 0.0224, 0.0127, 0.0112 for the synthetic
replay. The synthetic profile exists so that a reader can confirm the ambient layer changes
nothing structural: it shifts the dose by about one per cent and no decision changes.

Throughput is machine-dependent. The published evidence contains 30,915 instances per second
(`evidence/STRESS.md`, 200 passes) and 34,011 (`SW-10`, a single-pass benchmark on the same
machine). The criterion is 0 mismatches, not a speed.

## 5. Verification gates

| Gate | Command | Meaning |
|---|---|---|
| Project suite | `py -3.13 -m pytest tests/test_research_project_s.py tests/test_coldchain_engine_s.py tests/test_physics_layers_s.py tests/test_physical_gate_s.py tests/test_stats_s.py -q` | the artefact behaves as documented |
| Ambient data | `py -3.13 -m pytest tests/test_weather_regions_s.py -q` | the region table is integer, carries provenance, and differs from an invented table |
| Publication scrub | `py -3.13 -m pytest tests/test_research_scrub_s.py -q` | no personal or third-party data in the published tree |
| Document separation | `py -3.13 -m pytest tests/test_doc_separation_s.py -q` | see `PACKAGE.md`: no internal record reaches a published document |
| Style | `py -3.13 -m pytest tests/test_ascii_only_s.py tests/test_no_if_else_dispatch_s.py -q` | English and ASCII, rules as tables |

## 6. What is not reproducible from this tree

1. The complete repository test suite. It has failures unrelated to this programme, and the
   commands in section 5 are the ones that must pass.
2. A live weather forecast. The ambient table is a frozen climatology; a fresher snapshot is
   the same seam with different numbers, and it is not part of this release.
3. A commercial lane network. No purchased data is used anywhere, so the lane network and the
   scenario generator are synthetic and documented as such (`SW-02`, `SW-11`).
