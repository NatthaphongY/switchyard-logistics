# SW-SYS-04  -  Asset inventory of the host system

| Field | Value |
|---|---|
| Document ID | SW-SYS-04 |
| Kind | System record (internal; not published) |
| Version | 2.1 |
| Status | Baselined |
| Date | 2026-10-23 |
| Method | Filesystem inspection and executed commands; no values recorded from memory |
| Normative status | Informative |

## 1. Reusable components in the host system

Access is read-only. The programme MUST NOT modify these components.

| Component | Measured state | Use in this programme |
|---|---|---|
| `core/outline/math_engine.py` | 1,031 lines: Edmonds-Karp, critical path, Kernighan-Lin, entropy | Graph and scheduling core |
| `scripts/causal_spine_check.py` | 10,540 bytes: acyclicity, cycle listing, topological order | Dependency validation |
| `core/outline/transdisciplinary_math.py` | numpy and scipy: topological data analysis, Wasserstein distance | Only the measurable parts; the term sheaf MUST NOT be used until implemented |
| `scripts/spine_guard.py` | 27,571 bytes: rule gate with keyword-level transit validation | Validator prototype; requires a real state machine before use |
| `core/outline/story_gates.py`, `config/outline_gates.json` | Six or more fail-closed gates; rules held as data | Reference architecture for rule-as-data |
| `core/canon/ledger.py`, `config/canon_ledger/*.json` | Used, reserved, and retired registries with hashes | Provenance and audit reference |
| `core/ledger/*`, `scripts/drift_monitor.py` | Ledger, ten drift rules, schema baseline | Observability for long-running work |
| `scripts/outline_batch.py`, `data/outline_batch_state.json` | Batch execution with checkpoint | Resumable multi-day runs |
| `scripts/web_research.py` | 11,009 bytes: five free sources | Evidence collection |
| Test suite | More than 2,500 tests, executable locally | Regression protection |

## 2. Adjacent programme: game studio

Two directories are excluded from inspection by instruction: the studio documents
directory and the research and development repository.

| Asset | Measured state | Use in this programme |
|---|---|---|
| Unity project | 715 C# files | Entity-component-system architecture and simulation scale |
| Rust core prototype with foreign-function interface | Two source files | Candidate fixed-point deterministic core |
| Headless verification harness | 44 of 44 checks reported passing | Pattern for verification without launching the engine |
| Architecture decision records and system specifications | Five decision records plus coding and system specification documents | Decision-record discipline |
| Economic model reference documents | Four documents, 16.9 to 58.7 kilobytes | Demand and cost modelling structure |
| Geographic datasets | State dataset 114.5 kilobytes; world countries dataset 756.4 kilobytes | Base map and node generation |
| Binary format analysis | Two dissections, 56 and 23 kilobytes, plus decoder utilities | Reverse-engineering and decoder discipline |
| Design specification | 78.5 kilobytes | Example of a large specification controlled by numbers |

Conclusion: the transferable assets are the fixed-point deterministic core with its headless
harness, the architecture decision records, and the binary format decoders. The games
themselves are not transferable assets for this programme.

## 3. Required acquisitions

| Item | Reason | Responsibility |
|---|---|---|
| Reference implementation and reproducible baseline numbers | Required by gates B2 and B4 | Repository lead |
| Temperature and lane reference data, or an explicit synthetic assumption set | Required for any validation claim | Repository lead |
| One domain reviewer for cold-chain compliance | Prevents three to six months of misalignment | Repository lead |
| Tier-one chip design cost estimate | Required only if workstream A resumes | Repository lead |
