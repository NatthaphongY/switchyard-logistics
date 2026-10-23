# SW-02  -  Workstream B: Time-and-Temperature Critical Plans

| Field | Value |
|---|---|
| Document ID | SW-02 |
| Kind | Repository document (published) |
| Version | 2.0 |
| Status | Active |
| Date | 2026-10-23 |
| Deliverable | Event-agnostic compliance gate with a replayable dispatch release |
| Normative reference | SW-06 |
| Normative status | Informative |

## 1. Problem statement

Temperature-controlled goods, including vaccines, biologics, and fresh food, move across
several transport legs under two simultaneous constraints: a delivery window and a
temperature window. When a disruption occurs, the plan must be recomputed within hours
rather than weeks; otherwise delay and stock effects propagate through the supply chain.

Two errors are common in this domain:

1. Plans are tuned to a specific disruption and become useless when a different disruption
   occurs.
2. Monitoring is treated as the product, although monitoring does not recompute a plan.

## 2. Conditions recorded in 2026

| Observation | Source | Date |
|---|---|---|
| Market value USD 384.9 billion in 2026 and USD 555.4 billion in 2032, compound annual growth 6.34 per cent; temperature-controlled storage is 52.21 per cent of the total | Mordor Intelligence | page updated 2026-10-14 |
| Approximately two thirds of Far East to Europe capacity has returned to the Suez route | The Loadstar | 2026-10-21 |
| Suez container transits exceed 50 per cent of pre-crisis levels | El Estrecho Digital | 2026-10-14 |
| Full return to Suez expected during 2026 | Kuehne+Nagel report | 2026-08-18 |
| Six healthcare corridors added between Europe, North America, and Asia | DHL Group | 2026-10-12 |
| European cold-chain pharmaceutical booking digitised | FreightWaves | 2026-10-15 |
| Industry direction stated as prediction rather than visibility | Logistics Viewpoints | 2026-10-21 |

Consequences for this programme:

1. Any product whose value depends on a sustained canal closure is unsound. The gate must
   accept any disruption expressed as a parameter vector.
2. The visibility layer is commercially crowded. The gap is recalculation under thermal
   constraints.

## 3. Capability gap

| Required capability | Present | Evidence |
|---|---|---|
| Graph model of nodes and legs | Yes | A graph library with Edmonds-Karp minimum cut and a critical-path pass |
| Validation of travel mechanics | Partial, surface level | A keyword-membership check exists; it has no clock, coordinate, or custody state |
| Gates expressed as data | Yes | Rule tables in JSON, read by a fail-closed evaluator |
| Deterministic simulation | Yes, from an adjacent programme | Fixed-point core with a headless harness |
| Lane network with time windows and multiple modes | No | Not present in any form |
| Thermal model and excursion accounting | No | Not present in any form |
| Stochastic disruption and rolling-horizon replanning | No | Absent |
| Lane or customer data | No | Absent, and outside the zero-budget constraint |

## 4. Target architecture

```
[1] Lane model (data)        scenarios/lanes.json
      node: port | warehouse | railhead | airport, identified by UN/LOCODE where available
      lane: mode (sea, air, rail, road), transit, cost, capacity, temperature class
[2] Thermal model (physics)  lumped one-dimensional balance per container:
      dT/dt = (Q_ambient - Q_reefer) / C  -> excursion minutes per lane, season, dwell
[3] Event model (data)       six-axis vector; perturbs capacity, cost, and lead time
[4] Replanner                rolling horizon, minimum-cost flow on a time-expanded network;
      heuristic first, mathematical programming only if a gate demonstrates the need
[5] Gate (fail-closed)       rules are data; a failed plan is not released
[6] Scoring                  landed cost, 95th percentile lead time, excursion minutes,
      service level
```

Component [3] and all decision logic are specified normatively in SW-06.

## 5. Design rationale

The system models time, place, and condition over a graph. The structure is general rather
than domain-specific: a resource moves between places under a condition that decays, and a
controller decides when to intervene. Here the unit of measure is the hour, the degree, and
the currency, and the passing criterion is product integrity.


## 6. Acceptance criteria and termination

| Gate | Criterion | Evidence |
|---|---|---|
| B0 | A specification from which a third party predicts verdicts for five sample cases correctly | Four of five predictions correct |
| B1 | Lane dataset of at least 50 nodes and 150 lanes with temperature classes, open or documented as synthetic | Loads and validates; no event names in logic |
| B2 | Gate v0 with twenty gold cases | Twenty of twenty agree; identical hash across three runs |
| B3 | Event generator over six axes with damage patterns and a remedy menu | Unseen event vectors execute; no event-name branch |
| B4 | Measured against a greedy baseline on held-out event samples | At least 15 percentage points fewer unsafe control actions, or 10 per cent fewer excursion minutes |
| B5 | Public release and five-minute demonstration | One external reproduction of the same hash |

Termination criteria:

1. If B2 produces an unstable hash, work stops until determinism is achieved.
2. If B3 requires an event-name branch, the structure is incorrect and the work returns to
   phase P0.
3. If B4 shows no separation, the artefact may be released as a plan auditor rather than an
   optimiser, with the limitation stated in the first paragraph of SW-08.

## 7. Risks

| Risk | Mitigation |
|---|---|
| Real lane and rate data are commercial | Use open data, then a documented synthetic scenario pack |
| Visibility incumbents hold customer relationships | Compete on recalculation under constraint, not on tracking |
| Pharmaceutical buyers require validation evidence | Publish a method note and stated confidence; never publish a bare number |
| Disruption urgency is cyclical | Position the artefact as readiness, not crisis response |
| The word compliance may be read as regulatory certification | State explicitly that the gate certifies a plan against declared constraints only |

## 8. Event-agnostic discipline

| Rule | Enforcement |
|---|---|
| No event names in decision logic | Static scan of `gate/**` |
| Events enter only as six-axis vectors | Schema validation of `scenarios/*.json` |
| Named scenarios are data, never logic | Directory separation of data and logic |
| Larger magnitude never improves a verdict | Monotonicity test in the automated suite |
