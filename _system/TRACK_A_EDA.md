# SW-SYS-03  -  Workstream A: Semiconductor Floorplanning and Routing

| Field | Value |
|---|---|
| Document ID | SW-SYS-03 |
| Kind | System record (internal; not published) |
| Version | 2.1 |
| Status | Suspended on 2026-10-23, unstaffed |
| Date | 2026-10-23 |
| Resumption condition | Workstream B reaches gate B5, or the suspension is formally reversed |
| Normative status | Informative |

## 1. Status

This workstream is suspended. No tooling has been installed and no benchmarking has been
performed. The document is retained as the reference for a future resumption decision and
MUST NOT be cited as evidence of capability.

## 2. Prior assertion under assessment

The prior external review stated that the repository implements the same mathematics used
to route wires on a wafer, assigned a success probability of 85 per cent, and predicted an
acquisition approach by a large semiconductor company.

Assessment: the first clause is partially accurate (see SW-SYS-02, findings F-1 to F-4).
The remaining clauses have no supporting evidence (SW-SYS-02, findings F-8 and F-9).

## 3. Problem decomposition

| Layer | Problem | Required tooling |
|---|---|---|
| Partitioning | Partition a netlist of billions of gates with minimal cut | Hypergraph partitioning (KL, FM, hMETIS, KaHyPar) |
| Floorplanning | Place dissimilar macros with low half-perimeter wire length and no overlap | Simulated annealing, analytic placement, or reinforcement learning |
| Placement and legalisation | Place standard cells and snap to legal rows | Analytic placer with legaliser |
| Global routing | Route nets through routing cells within congestion limits | Minimum-cost flow, Steiner trees, rip-up-and-reroute |
| Detailed routing and design rule checking | Route to foundry rules | Process design kit and rule deck, normally under non-disclosure |
| Sign-off | Timing, power, IR drop, electromigration, thermal | Certified commercial tools |

The problems are NP-hard; a fast, reproducible, near-optimal answer has commercial value.

## 4. Present versus absent capability

| Required capability | Present | Evidence |
|---|---|---|
| Graph minimum cut and maximum flow | Yes | SW-SYS-02, F-1 |
| DAG ordering and cycle detection | Yes | SW-SYS-02, F-2 |
| Critical path and slack | Yes | SW-SYS-02, F-3 |
| Deterministic execution with resume and audit | Yes | `scripts/outline_batch.py`, `core/ledger/*` |
| Gates expressed as data | Yes | `config/outline_gates.json`, `core/outline/story_gates.py` |
| Hypergraph partitioning | No | Search log, SW-SYS-02 section 6 |
| LEF, DEF, or Verilog parsing | No | Search log, SW-SYS-02 section 6 |
| Congestion, thermal, or static timing analysis | No | Search log, SW-SYS-02 section 6 |
| Process design kit and rule deck | No | Not available without agreements |
| Comparable benchmark set | No | Not present on this machine |

### Technical distinction that must not be lost

The minimum cut implemented here operates on a **graph**, in which an edge connects two
nodes and carries a capacity. Partitioning in electronic design automation operates on a
**hypergraph**, in which a net connects many pins simultaneously. The theory remains valid
as a tool, but the object differs. Applying the existing implementation unchanged and
declaring completion is the specific failure mode this document exists to prevent.

## 5. Market conditions recorded in 2026

- The electronic design automation tools market is valued at USD 20.78 billion in 2026 and
  USD 30.67 billion in 2031, a compound annual growth rate of 8.1 per cent, with high
  concentration (Mordor Intelligence, page updated 2026-10-14).
- Synopsys completed the acquisition of Ansys for USD 35 billion in 2025, consolidating
  silicon-to-system coverage.
- OpenAI and Synopsys announced a joint model that operates electronic design automation
  tools (reported 2026-10-06).
- Synopsys moved to a royalty and model revenue-sharing structure at its 2026 investor day
  (reported 2026-10-02).
- Industry commentary identifies evidence-driven automation as the emerging requirement
  (Semiconductor Engineering, 2026-09-24).

The available opening is verifiable evidence of improvement, not a new model. This aligns
with the repository's verification discipline and argues against competing on generative
design agents.

## 6. Candidate entrances, if the workstream resumes

One candidate only; each is executable on central processing units without design kit access:

1. Hypergraph partitioner benchmarked against KaHyPar or hMETIS on an open benchmark,
   measured by cut size and runtime.
2. Legaliser benchmarked against OpenROAD `dpl`, measured by displacement, wire length, and
   runtime.
3. Congestion estimator benchmarked against the OpenROAD estimator, measured by mean
   absolute percentage error per routing cell.

## 7. Acceptance criteria

| Level | Criterion | Required evidence |
|---|---|---|
| A-1 | Open toolchain completes on this machine | Log, wall clock, input and output hashes |
| A-2 | Baseline measured with a reference implementation | Numeric table per benchmark |
| A-3 | Equal or better result on at least one metric within twice the runtime | Comparison table and reproduction script |
| A-4 | Independent reproduction of identical numbers | Issue or comment from a third party |
| A-5 | Use or citation by a practitioner | Not required to be commercial |

Termination criterion: if A-3 is not achieved within twelve weeks of substantive work, the
workstream stops or descends to a smaller scope, such as an automated floorplan checker.

## 8. Risks

1. Process design kit and rule decks are released only under agreement; without them there
   is a hard ceiling on credibility.
2. Incumbent tooling plus announced artificial-intelligence partnerships are absorbing
   tool-driving agents quickly.
3. Feedback latency is weeks, which is materially slower than document production.
4. Sustained effort below 15 hours per week reduces the artefact estimate in SW-SYS-02
   section 5 substantially.
