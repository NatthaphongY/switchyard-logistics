# SW-SYS-01  -  Decision log (system record)

| Field | Value |
|---|---|
| Document ID | SW-SYS-01 |
| Kind | System record (internal; not published) |
| Version | 1.1 |
| Status | Active |
| Date | 2026-10-23 |
| Machine record | `programme.json` in this directory; this file is its readable form |
| Scope | Decisions, the questions they answer, product-name prior art, and the business context that is not published |

## 1. How this record is used

A decision recorded here is a fixed input until it is formally revised. A revision is a
new entry with a later date that names the entry it supersedes; entries are never edited
in place, so the history stays readable. Where two entries conflict, the entry that names
the other governs. The date column records when the entry was written into this registry,
which is not always the day the decision was taken: the registry was consolidated in one
sitting, and the ordering of the list carries the sequence.

Only the consequences of a decision belong in a published document. The decision itself,
the alternatives that were rejected, and the commercial reasoning stay here. The published
documents state what the artefact does and how a reader reproduces it;
`tests/test_doc_separation_s.py` fails if a decision identifier or an owner reference
reaches `README.md`, `PACKAGE.md` or `docs/`.

## 2. Programme decisions

| ID | Decision | Date | Reference |
|---|---|---|---|
| D-1 | No external investment and no return-on-investment defence. | 2026-10-23 |  |
| D-2 | Business Source Licence 1.1 with an Additional Use Grant, paired with a specification under Apache-2.0. | 2026-10-23 |  |
| D-3 | Elaborate mathematical machinery is permitted in this programme and prohibited on the host production tree. Re-import requires evidence and a proposal. | 2026-10-23 |  |
| D-4 | Logistics is the active workstream. Electronic design automation is suspended and unstaffed. | 2026-10-23 |  |
| D-5 | The event model is event-agnostic. Named events MUST NOT appear in decision logic. | 2026-10-23 |  |
| D-6 | Data acquisition budget is zero. Only openly licensed data is used. | 2026-10-23 |  |
| D-7 | Primary objective is professional reputation and a verifiable public artefact. Revenue is a secondary consequence. | 2026-10-23 |  |
| D-8 | Schedule is 35 working days. The 90-day plan is withdrawn. Superseded by D-18, which re-baselines to five to seven working days. | 2026-10-23 | superseded by D-18 |
| D-9 | The event model is layered, not six-dimensional: six physical axes plus propagation (4), information (2), institutions (3) and four catalyst domains with twelve indices. | 2026-10-23 | SW-09 |
| D-10 | Cascades are modelled as a branching process with k_eff = fanout x susceptibility x (1 + catalyst pressure), plus a percolation check on the largest connected component. Limits are stated: synthetic calibration only. | 2026-10-23 | SW-09 section 3 and section 7 |
| D-11 | Four structural catalysts are first-class: geoeconomic fragmentation, workforce volatility, credit and liquidity, cyber insecurity. Each adds gate codes rather than new narrative vocabulary. | 2026-10-23 | SW-09 section 6 |
| D-12 | All gate and planner decisions use integer micro-units and integer minutes, reusing ADR-001 of the host engine. Floating point is confined to transport and reporting. | 2026-10-23 | SW-10 |
| D-13 | Two implementations exist: the Python reference and a dependency-free Rust core. Conformance is proved by replaying exported instances; 300 of 300 agree. Release hashes are produced on the integer CPU path, never in a shader. | 2026-10-23 | SW-10 sections 4 to 6 |
| D-14 | Gate B4 is decided by a paired bootstrap with a zero guard band and a pre-registered ladder that raises coupling without lowering the bar. Both limbs must be reported even when only one is met. | 2026-10-23 | SW-08 |
| D-15 | Licence change date is two years from first public release. Two years is shorter than the BUSL-1.1 maximum of four, so it is compliant and reaches open source sooner. This supersedes the four-year answer for open decision 1. | 2026-10-22 |  |
| D-16 | If gate B4 is non-separating, the artefact may be released as a plan auditor with reduced scope, provided SW-08 states the limitation in its first paragraph. | 2026-10-22 |  |
| D-17 | No external domain reviewer is appointed. Limitations are recorded in SW-03, SW-11 and SW-12 instead of being hidden. | 2026-10-22 |  |
| D-18 | The schedule is re-baselined to five to seven working days. Supersedes D-8. The 35-day plan is withdrawn as unrepresentative of the work; this supersedes D-8. | 2026-10-22 |  |
| D-19 | A physical layer is adopted only when it changes a decision, and its constants live in config/physics.json. Fields that do not change a decision stay in the survey, not in the code. | 2026-10-22 |  |
| D-20 | The research tree is English and code only, with no CJK characters, and contains no if/elif dispatch: rules live in tables. Both rules are enforced by tests, not by review. | 2026-10-22 |  |
| D-21 | Superseded by D-24. The product name is Switchyard. Prior art was checked before adoption: the name is already used by an unrelated educational networking framework on the Python Package Index, so a Python distribution would need a suffix. | 2026-10-23 | programme.json, product_name |
| D-22 | Ambient weather data is open reanalysis only: the free, keyless Open-Meteo archive API serving ERA5, frozen as a July 1991-2020 climatology in config/weather_regions.json. A live forecast ingest is out of scope until a consumer needs one. | 2026-10-23 | SW-11 |
| D-23 | Separation precedes new work. From 2026-10-23 this tree is a standalone repository: the copy held inside the host tree is extracted, the guard modules travel with it, and nothing here is a worktree of the host. The three candidate projects are deferred. Re-entry into the host system, and the repair of pain points in it, are recorded directions rather than scheduled work, and re-entry happens as a dependency or as a ported mechanism with tests, never by copying files into the host tree. | 2026-10-23 | SW-SYS-09 |
| D-24 | The product name is switchyard-logistics, by the owner's instruction on 2026-10-23; D-21 is superseded. The distribution name in pyproject.toml already carried the qualifier because `switchyard` is taken on the Python Package Index. The registry id SW-xx, the import package `switchyard` and the Rust binary `switchyard-core` are identifiers and are unchanged, so no document is renumbered and no import moves. | 2026-10-23 | programme.json, product_name |
| D-25 | The earlier commit enters this repository as an ancestor, and the host copy is deleted only after three checks. Commit 8c4d712a is carried by a root commit whose tree is its research/ subtree byte for byte (0214f168) with the original author, date and message, merged into this branch with the ours strategy, so the ancestry is restored without moving the tree. Deletion was cleared by: all 147 refs of the copy resolving to objects the host repository holds; all 58 uncommitted paths captured in `_system/host_transfer/` with a hash each; and 37 files written inside the copy after it was made classified, the 20 that nothing else carried archived. Deleting a duplicate without those three checks is a guess, not a cleanup. | 2026-10-23 | SW-SYS-TRANSFER, SW-SYS-06 |

## 3. Answers given before the record was opened

| # | Question | Answer | Date |
|---|---|---|---|
| 1 | approve installation of an electronic design automation toolchain? | not required; EDA suspended | 2026-10-23 |
| 2 | data budget? | $0, open data only | 2026-10-23 |
| 3 | workstream order? | logistics first; EDA suspended | 2026-10-23 |
| 4 | primary objective? | reputation and portfolio; revenue secondary | 2026-10-23 |
| 5 | documentation language and style? | professional English; decorative markers prohibited | 2026-10-23 |
| 6 | Business Source Licence change date | Two years (D-15); four years is the legal maximum, not the chosen value | 2026-10-23 |
| 7 | Which ambient weather data may the research programme use? | Free open reanalysis only: Open-Meteo archive API (ERA5), keyless, no account | 2026-10-23 |

## 4. Questions put to the owner

| # | Question | Options | Status | Resolution | Date |
|---|---|---|---|---|---|
| 1 | Business Source Licence change date: four years or two years? | 4y, 2y, unspecified | resolved | Two years, per D-15. Four years remains the legal maximum, not the chosen value. | 2026-10-22 |
| 2 | May a non-separating result at gate B4 be released as a plan auditor? | yes, specification only | resolved | Yes, per D-16, with the limitation stated in SW-08. In this run the gate separates, so the fallback is unused. | 2026-10-22 |
| 3 | What is the product name? The artefact is referred to by registry id SW until the owner decides. | Switchyard | resolved | switchyard-logistics, fixed by the owner on 2026-10-23 (D-24) and recorded here as the product name. The registry id SW-xx stays as the document and gate identifier, so no document has to be renumbered. Prior art checked the same day: the name is used by an unrelated educational networking framework published on the Python Package Index (switchyard 1.0.1, GPLv3) and by a retired integration product. Both are different fields, so the name is usable as a product name; it is NOT usable as a Python distribution name, which must carry a suffix (for example switchyard-logistics) if anything is ever published. | 2026-10-23 |
| 4 | Which licence text goes in `LICENSE`, and who is the holder: the person or an entity? | person, entity, defer | open | Deferred by the owner on 2026-10-23. The record declares Apache-2.0 for the specification and a source-available posture for the code, but no `LICENSE` file exists yet, and the gate that keeps personal names out of published files stands in the way of a holder line until the question is answered. | 2026-10-23 |

## 5. Product name and prior art

| Field | Value |
|---|---|
| Product name | Switchyard |
| Date | 2026-10-23 |
| Scope | Product name only. Document and gate identifiers stay SW-xx, so evidence filenames, thresholds and imports are unchanged. |

| Prior use | Detail | Consequence |
|---|---|---|
| switchyard on the Python Package Index | Version 1.0.1, an educational networking framework by Joel Sommers, GPLv3 | Different field, so the product name is free; a Python distribution would need a suffix |
| Switchyard, an enterprise integration product | Retired; no current product in this field under the name | No confusion with logistics planning |

## 6. Business context (not published)

| Subject | Finding | Source | Date |
|---|---|---|---|
| Cold chain logistics market | size 2026 USD 384.9B size 2032 USD 555.4B cagr 6.34 per cent | Mordor Intelligence | 2026-10-23 |
| Suez route recovery | fact approximately two thirds of Far East to Europe capacity returned to Suez consequence a product premised on a permanent closure is unsound | The Loadstar | 2026-10-21 |
| Electronic design automation market (suspended workstream) | size 2026 USD 20.78B size 2031 USD 30.67B cagr 8.1 per cent | Mordor Intelligence | 2026-10-23 |
| Incumbent partnership (suspended workstream) | fact OpenAI and Synopsys announced a joint model that operates electronic design automation tools | Tom's Hardware | 2026-10-06 |

Goal of the programme, as recorded in `programme.json -> goal`: primary objective is
`reputation_portfolio`; secondary is `optional_revenue`. Re-import into production follows `import_back_policy` in the
same file: a proposal, an owner approval, and an implementation with tests, in that order.

