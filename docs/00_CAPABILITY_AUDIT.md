# BHR-RS-00  -  Capability Audit

| Field | Value |
|---|---|
| Document ID | BHR-RS-00 |
| Version | 2.0 |
| Status | Baselined |
| Date | 2026-10-23 |
| Scope | Optimisation and verification mechanisms of the Bar H Ranch Publishing System |
| Method | Source inspection, executed tests, executed probe values |
| Normative status | Informative; findings are binding on planning documents |

## 1. Purpose and method

A prior external review asserted that the repository contains mathematics suitable for
electronic design automation and for military logistics planning, and attached success
probabilities of 85 and 75 per cent. This audit tests those assertions.

The audit does not accept naming as evidence. For every claim, three steps are performed:

1. Read the implementing source and record its location as `path:line`.
2. Execute the test suite that covers the mechanism.
3. Execute probe values whose expected output is known, and record the observed output.

A claim is classified as one of:

| Class | Definition |
|---|---|
| Confirmed | The mechanism exists as named and behaves as described |
| Label-only | The name is present; the implementation computes something materially simpler |
| Degenerate | The implementation is algebraically reducible to a constant or trivial rule |
| Unsupported | No implementation exists in the repository |

## 2. Findings

| ID | Claim | Class | Evidence |
|---|---|---|---|
| F-1 | Edmonds-Karp minimum cut | Confirmed | `core/outline/math_engine.py:236-237` calls `nx.minimum_cut(..., flow_func=nx.algorithms.flow.edmonds_karp)` with networkx 3.6. `tests/test_true_graph_engines_s.py` passes 6 tests in 1.28 s. |
| F-2 | Directed acyclic graph ordering and cycle detection | Confirmed | `scripts/causal_spine_check.py:71-73` uses `nx.is_directed_acyclic_graph`, `nx.simple_cycles`, and `nx.topological_sort`, with reachability. |
| F-3 | Critical path method | Confirmed | `core/outline/math_engine.py:247-268` implements a forward pass (earliest start), a backward pass (latest finish), `slack = ls - es`, and criticality defined by zero slack. |
| F-4 | Retargeting from narrative entities to physical nodes is structurally feasible | Confirmed | The graph layer is a generic `DiGraph` over nodes and capacities; node semantics are not bound to narrative data. |
| F-5 | Cellular sheaf cohomology | Label-only | `core/outline/transdisciplinary_math.py:133-168` computes `gap = ||r_k - c_k||_2` at line 157. No stalks, restriction maps, coboundary operator, or cohomology groups are implemented. |
| F-6 | Non-equilibrium thermodynamic speed limit | Degenerate | Lines 194-198 define `sigma = dT^2 * I` and `v_bound = sqrt(2*sigma/(tau_r*I))`, so `I` cancels and `v_bound = |dT| * sqrt(2/tau_r)`. With the default `tau_r = 3`, the effective rule is a constant threshold `|dT| > 1.09`. Probes: `dT = 0.9` passes, `dT = 1.2` fails. |
| F-7 | Three-phase spatial-temporal transit state machine | Degenerate | `scripts/spine_guard.py:131-145` tests list membership of keywords at line 135. A single arrival phrase passes with no departure present, and no clock or coordinate state exists. |
| F-8 | The system is an EDA tool or a military logistics blueprint | Unsupported | No hypergraph partitioning, LEF/DEF/Verilog parsing, static timing analysis, congestion or thermal mapping, design rule checking, MILP/VRP/time-window scheduling, multi-commodity flow, or reefer thermal model exists. Search log in section 6. |
| F-9 | Success probabilities of 85 and 75 per cent | Unsupported | No benchmark, customer data, or domain artefact supports a point estimate. Section 4 replaces them with ranges and stated conditions. |

## 3. Assets the prior review did not identify

The following capabilities are present and are more transferable than the graph algorithms.

| Asset | Relevance to industrial planning |
|---|---|
| Gates expressed as data (`config/outline_gates.json`, `config/canon_ledger/*.json`) | Sign-off rule sets change per process node or per jurisdiction; rule-as-data with fail-closed behaviour is typically rebuilt poorly by domain teams |
| Deterministic batch execution with checkpoint and resume (`scripts/outline_batch.py`, `data/outline_batch_state.json`) | Design and planning runs extend over days; resumability is a requirement, not a feature |
| Fail-closed gates with an extensive regression suite | Both target industries evaluate suppliers on trust and repeatability rather than raw speed |
| Provenance registries with content hashes (`core/canon/ledger.py`, `core/ledger/*`) | Auditors require a defensible record of every decision |
| Fixed-point deterministic core with a headless verification harness | Bit-exact reproducibility is a precondition for any digital twin |


## 4. Transferability of the "do not accept scepticism" argument

A widely used argument in this repository states that a prediction of failure is not
evidence of failure, because a prior creative programme succeeded despite such predictions.
The argument is valid as a general principle. Its transfer to industrial domains is partial,
because the criterion of quality changes.

| Dimension | Creative production | Industrial planning |
|---|---|---|
| Quality criterion | Reader acceptance and commercial outcome | Measured deviation from a reference implementation |
| Availability of a correct answer | No single correct answer exists | Incorrect answers are demonstrable within minutes |
| Gate | Editorial approval | Benchmark, design-rule checking, audit |
| Cost of entry | Low | High: licences, non-disclosure access, staff, trust |

The transferable lesson is that third-party predictions carry no evidential weight. The
non-transferable inference is that capability therefore follows, because the gate changes
from taste to measurement against a reference.

A compensating property favours this programme: industrial results are measurable, so a
positive result is defensible without argument, and a negative result is discovered early
at low cost.

## 5. Probability assessment

The following ranges replace the point estimates in F-9. They are derived from the state of
the repository on 2026-10-23 and from the evidence register in BHR-RS-03. No customer
interviews or domain advisor input is included, which is a material limitation.

| Workstream | Outcome | Range | Conditions that move the estimate |
|---|---|---|---|
| A | Commercial EDA vendor | 0.10 to 0.15 | Requires a team, process design kit access, and two to three years. Solo effort: below 0.05 |
| A | Cited open artefact within six months | 0.50 to 0.60 | Requires 15 to 20 hours per week sustained. Below that: approximately 0.25 |
| B | Reproducible gate artefact within 35 working days | 0.80 to 0.90 | The limiting factor is definition and packaging, not technology |
| B | External citation or use within six months | 0.25 to 0.40 | Depends on publication quality and on addressing a recognised problem |
| B | Paid pilot at any time | 0.15 to 0.25 | Requires a sales function and ten or more qualified conversations |

Workstream B is rated higher than workstream A although the prior review rated A higher.
Access barriers in A, namely process design kit access, non-disclosure agreements, incumbent
trust, and an announced incumbent partnership with an artificial-intelligence laboratory,
are measured in years. The barrier in B is customer access, which can be tested in ten
conversations, while the artefact itself can be produced from assets already present.

## 6. Absence-of-capability search log

The following searches returned no matches, which supports F-8.

| Pattern | Result |
|---|---|
| `route_chip`, `place_blocks`, `legaliz` | 0 |
| `LEF`, `DEF`, `Verilog`, `.lib` parser | 0 |
| `congestion`, `HPWL`, `wirelength` | 0 |
| `milp`, `vrp`, `time_window`, `multi_commodity` | 0 |
| `reefer`, `excursion`, `cold_chain` | 0 |

## 7. Reproduction procedure

```powershell
py -3.13 -m pytest tests/test_true_graph_engines_s.py -q
# expected: 6 passed

py -3.13 -X utf8 -c "from core.outline.transdisciplinary_math import compute_thermodynamic_speed_limit as f; [print(n, f([0.2, 0.2+n])['speed_limit_passed']) for n in (0.9, 1.2)]"
# expected: 0.9 True, 1.2 False

py -3.13 -X utf8 -c "from scripts.spine_guard import evaluate_spatial_transit_bridge as f; print(f('\u0e25\u0e07\u0e08\u0e2d\u0e14\u0e17\u0e35\u0e48\u0e1a\u0e32\u0e01\u0e23\u0e31\u0e21', ['\u0e40\u0e17\u0e35\u0e48\u0e22\u0e27\u0e1a\u0e34\u0e19', '\u0e40\u0e17\u0e04\u0e2d\u0e1f', '\u0e25\u0e07\u0e08\u0e2d\u0e14']))"
# expected: (True, 'valid_transit')
# The literal is an arrival-only phrase. It is escaped so this document remains ASCII.
```

## 8. Audit maintenance

Findings are pinned by automated tests. If any mechanism in F-5, F-6, or F-7 is implemented
to the standard its name implies, the corresponding test fails and this document MUST be
revised in the same change. Findings MUST NOT be restated as capabilities without new
evidence.
