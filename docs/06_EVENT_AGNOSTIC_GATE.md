# BHR-RS-06  -  Event-Agnostic Compliance Gate: Specification

| Field | Value |
|---|---|
| Document ID | BHR-RS-06 |
| Version | 1.1 |
| Status | Normative; governs all gate implementations |
| Date | 2026-10-22 |
| Licence | Apache-2.0 |
| Keywords | The key words MUST, MUST NOT, SHOULD, SHOULD NOT, and MAY are to be interpreted as described in RFC 2119 |

## 1. Scope

This specification defines a compliance gate for plans that carry simultaneous time and
temperature constraints. The gate evaluates a plan against declared constraints and returns a
verdict together with a dispatch release.

The specification covers the event model, the damage patterns, the unsafe control actions,
the verdict vocabulary, the finding schema, the remedy vocabulary, and the determinism
requirements.

The specification does not cover route optimisation algorithms, transport management
functions, warehouse management functions, or any regulatory certification.

## 2. Terminology

| Term | Definition |
|---|---|
| Plan | An ordered set of legs with assigned mode, departure window, and assigned equipment |
| Leg | Movement of one consignment between two nodes by one mode |
| Node | A port, warehouse, railhead, or airport |
| Temperature class | A defined admissible temperature interval, optionally with an excursion allowance |
| Excursion | Accumulated time outside the admissible interval of the assigned class |
| Damage pattern | A measurable signal indicating that a plan is degrading, independent of the cause |
| Unsafe control action | A control decision that is hazardous even in normal conditions |
| Finding | A structured record comprising a code, severity, location, measurement, and remedies |
| Dispatch release | The signed output of the gate comprising a verdict, findings, and conditions |
| Condition | An executable predicate that MUST hold before departure |
| Event vector | The six-axis representation of a disruption |

## 3. Event model

A disruption MUST be represented as a vector over six axes. An implementation MUST NOT
branch on the name of an event.

| Axis | Admissible values | Required semantics |
|---|---|---|
| `onset_rate` | `instant`, `gradual` | `instant` requires evaluation against slack available at decision time; `gradual` requires evaluation of excursion drift |
| `notice_min` | `0`, `hours`, `days` | `0` prohibits reliance on any approval step that cannot complete before departure |
| `duration` | `hours`, `days`, `weeks`, `months` | `weeks` or `months` requires structural remedies rather than rerouting |
| `magnitude` | Object with `capacity_loss`, `lead_time_inflation`, `cost_inflation`, each a percentage | Numeric, never boolean |
| `scope` | `node`, `lane`, `region`, `global` | Determines which remedies are admissible |
| `reversibility` | `recoverable`, `structural` | `structural` prohibits waiting as a remedy |

These six axes are the physical layer. Propagation, information, institutional and
catalyst layers are defined normatively in BHR-RS-09; they produce network facts
and verification flags, never event names, and the gate MUST NOT branch on them.

Requirements:


## 4. Damage patterns

An implementation MUST evaluate the following patterns. Each pattern is independent of the
cause of the disruption.

| ID | Pattern | Measurement | Mechanism | Consequence if ignored |
|---|---|---|---|---|
| D1 | Excessive dwell | Time at a node exceeding that node's 95th percentile | Per-node statistic over open or historical data | Spoilage and equipment detention |
| D2 | Thermal drift | Rate of temperature change exceeding available cooling capacity | Lumped thermal balance; see section 12 | Excursion allowance exhausted |
| D3 | Broken handoff | Missing accountable party, document, or timestamp at a custody boundary | Chain structure traversal | Loss, unmonitored interval, no traceability |
| D4 | Slack exhaustion | Critical-path slack less than or equal to zero | Critical path method; already implemented in the host system | Unavoidable lateness |
| D5 | Capacity collapse | Maximum flow below demand | Minimum cut; already implemented in the host system | Consignment cannot be moved |
| D6 | Stale decision | Age of the decision input exceeding the freshness limit | Per-field timestamps | Decision taken against an obsolete state |

The D4 and D5 mechanisms are confirmed in BHR-RS-00 findings F-3 and F-1. Pattern D2 is a
hypothesis model and MUST be labelled as such in any output.

## 5. Unsafe control actions

Derived from system-theoretic process analysis: the gate evaluates control decisions rather
than predicted failures, which is the property that makes it event-agnostic.

| ID | Unsafe control action |
|---|---|
| UCA1 | Release of a refrigerated container without verified pre-cooling |
| UCA2 | Release with slack below the maximum handoff time |
| UCA3 | Acceptance of a reroute that removes temperature monitoring coverage |
| UCA4 | Consolidation of two temperature classes in one container |
| UCA5 | Departure on data older than the freshness limit |
| UCA6 | Acceptance of an excursion without a documented disposition |
| UCA7 | Release when the receiving site has not confirmed a door |
| UCA8 | Use of a backup node whose capacity has not been assessed |
| UCA9 | Dependence on a single mode while that mode has an open blocking condition |
| UCA10 | Acceptance of a cost reduction without recomputing excursion minutes |
| UCA11 | Release without a per-leg accountable party |
| UCA12 | Acceptance of a plan requiring approval when event notice is zero |
| UCA13 | Release across a controlled border without a permit on file |
| UCA14 | Release through a station whose throughput is unavailable |
| UCA15 | Release against a counterparty whose solvency is unverified |
| UCA16 | Release while custody records cannot be verified against the system of record |
| UCA17 | Release through a station already at or above the utilisation ceiling |
| UCA18 | Release of a consignment whose projected thermal dose exceeds its quality budget |
| UCA19 | Release on a route whose series availability is below the floor |
| UCA20 | Triage that leaves deliberate deferral above the service ceiling |

## 5a. Plan facts the gate consumes

A plan is a list of legs plus the compliance actions it paid for. Each action is a
field on the plan, and each field is the only way to clear its finding:

| Plan field | Clears | Price key in `config/physics.json` |
|---|---|---|
| `pre_cool_verified` | `GATE-TEMP-002` | `pre_cool_per_unit` |
| `input_refreshed` | `GATE-DATA-001` | `refresh_feed_min` |
| `capacity_measured` | `GATE-DATA-002` | `capacity_measure_min` |
| `pre_authorised` | `GATE-PLAN-002` | `pre_authorisation_per_unit` |
| `out_of_band_verified` | `GATE-HANDOFF-003` | `out_of_band_verify_min` |
| `escrowed` | `GATE-PARTY-001` | `escrow_permille_of_value` |
| `backup_modes` | `GATE-MODE-001`, `GATE-RELIAB-001` | `backup_mode_permille_of_leg` |
| `thermal_protection` | `GATE-THERM-006` | `thermal_protection_per_unit` |
| `prepositioned` | `GATE-FLOW-001` | `preposition_per_unit` |
| `deferred` | `GATE-SERVICE-001` (by pushing served below the floor) | `deferral_per_unit` |

The rule is symmetric: an action that is not recorded is not paid for, and a
finding that is not cleared stands. `evaluate.prepare()` applies the event facts
and the plan facts in one place, as a table (`AUTHORITY_RULES`), so no call site
can accidentally grant an exception.

## 6. Verdict and dispatch release

The gate MUST return exactly one verdict from the following vocabulary.

| Verdict | Condition | Authority to release |
|---|---|---|
| `PASS` | No finding of severity `block` or `warn` | System |
| `PASS_WITH_CONDITION` | At least one `warn` finding, each associated with an executable condition | System with human confirmation of the conditions |
| `BLOCKED` | At least one `block` finding | None; the plan must change |

A numeric score MUST NOT be returned as a verdict.

The release MUST contain: release identifier, plan hash, verdict, ordered findings,
conditions, excursion budget usage, random seed, and a replay hash.

```
DISPATCH RELEASE   release_id: R-2026-1023-0007   plan_hash: 9f2c...a41d
VERDICT: PASS_WITH_CONDITION

[GATE-SLACK-002] warn  leg L07  slack 46 min, required 90 min
                 remedy: shift departure by 60 min, or reserve a slot at destination
[GATE-TEMP-004]  block leg L11  thermal drift 0.42 C/h, capacity 0.30 C/h
                 remedy: pre-cool by 5 C, or change to temperature class B

CONDITIONS
  C1 departure[L07] >= plan + 60 min
  C2 pre_cool_verified[L11] = true

EXCURSION BUDGET used 0 min of 30 min; frozen class allows 0 min
REPLAY seed 7; three runs identical; sha256_16 9f2c...
```


1. An implementation MUST reject a vector with an unknown axis or an out-of-range value.
2. An implementation MUST treat a missing axis as a blocking error, not as a default.
3. The verdict MUST be monotone in `magnitude`: increasing a magnitude MUST NOT improve the
   verdict.

Example vector, representing a regional capacity loss of 35 per cent with no notice:

```json
{"onset_rate": "instant", "notice_min": 0, "duration": "days",
 "magnitude": {"capacity_loss": 0.35, "lead_time_inflation": 0.20},
 "scope": "region", "reversibility": "recoverable"}
```

## 7. Gate codes

Each finding MUST carry a stable code, a severity, a location, the measured value, and one
or more remedies.

| Code | Severity | Detection | Remedy |
|---|---|---|---|
| `GATE-TEMP-001` | block | Mixed temperature classes in one container | Split the consignment or change class |
| `GATE-TEMP-002` | block | No verified pre-cooling | Pre-cool and record the temperature before departure |
| `GATE-TEMP-003` | warn | No sensor coverage on a leg | Add a logger or change the leg |
| `GATE-TEMP-004` | block | Thermal drift exceeds cooling capacity | Pre-cool, change class, or reduce dwell |
| `GATE-SLACK-001` | block | Slack less than or equal to zero | Shift departure or change mode |
| `GATE-SLACK-002` | warn | Slack positive but below the maximum handoff time | Shift departure or reserve a slot |
| `GATE-FLOW-001` | block | Maximum flow below demand | Add capacity or reduce batch size |
| `GATE-HANDOFF-001` | block | Missing accountable party for a leg | Name the party and the handover time |
| `GATE-HANDOFF-002` | warn | Receiving door not confirmed | Confirm the door |
| `GATE-DATA-001` | block | Decision input older than the freshness limit | Refresh the input or replan |
| `GATE-PLAN-001` | warn | Cost reduction accepted without recomputed excursion | Compute excursion before comparison |
| `GATE-PLAN-002` | block | Approval required while event notice is zero | Establish pre-authorisation |
| `GATE-DATA-002` | block | Capacity assumption unverified | Verify the capacity assumption or replan |
| `GATE-LEGAL-001` | block | Cross-border leg without a permit on file | Hold the permit or use an uncontrolled border |
| `GATE-NODE-002` | block | Station throughput unavailable at departure or arrival | Use a station with available throughput |
| `GATE-PARTY-001` | block | Counterparty solvency unverified | Verify solvency or escrow the leg |
| `GATE-HANDOFF-003` | block | Custody records cannot be verified | Verify the handoff record out of band |
| `GATE-QUEUE-001` | block | Station utilisation above the configured ceiling | Spread the load, add a server, or route through a station below the ceiling |
| `GATE-THERM-006` | block | Thermal dose above the quality budget | Cut uncontrolled exposure, add active cooling, or reduce the batch |
| `GATE-RELIAB-001` | block | Series availability below the floor | Book a backup mode or shorten the series route |
| `GATE-SERVICE-001` | block | Deliberate deferral leaves service below the floor | Serve the floor before triaging low-criticality volume |

The last four are the physical layers (BHR-RS-11). They are computed from integer
metrics only, and they are rows in `gate.PHYSICAL_RULES`: the evaluator is one
loop, so a new rule is a new row rather than a new branch.

Finding schema:

```json
{"code": "GATE-TEMP-004", "severity": "block", "pattern": "D2",
 "span": {"leg": "L11", "from_min": 180, "to_min": 425, "field": "temp_c"},
 "measured": {"rate_c_per_h": 0.42, "capacity_c_per_h": 0.30},
 "remedies": ["pre_cool:-5C", "temperature_class:B"], "unsafe_control_actions": ["UCA1"]}
```

## 8. Remedy vocabulary

An implementation MUST use only the following remedy classes, and MUST report which classes
produce a passing plan together with the associated measurement.

| Remedy | Action | Admissible when |
|---|---|---|
| `SHIFT` | Move departure or arrival in time | Slack remains but dwell is projected to exceed the node threshold |
| `ABSORB` | Increase cooling capacity or pre-cool | Thermal drift is still controllable |
| `BUFFER` | Hold safety stock or reserve a slot | Magnitude high with wide scope |
| `REROUTE` | Change leg or mode | Capacity collapse |
| `HOLD` | Stop and wait, accepting delay | Reversibility is structural |
| `DOCUMENT` | Accept the excursion with a recorded disposition | The excursion has already occurred |

The gate MUST NOT select a remedy on behalf of the operator. It reports which remedies pass
and which do not.

## 9. Determinism and replay

1. Decision arithmetic MUST use fixed-point integers or decimal representation. Binary
   floating point MUST NOT appear in a decision path.
2. Serialised input and output MUST be canonical: sorted keys, stable separators, UTF-8
   without a byte order mark.
3. The random seed MUST be explicit in the release, and the generator MUST be owned by the
   implementation.
4. Hashes MUST form a chain from plan to release, including input hashes and the
   specification version.
5. Three consecutive runs MUST produce identical hashes before a result is considered valid.

## 10. Conformance

An implementation is conformant when it satisfies sections 3 to 9 and passes the reference
case set.

| Group | Cases | Requirement |
|---|---|---|
| Normal | 5 | Verdict `PASS` with no findings |
| Missing custody or documentation | 5 | Verdict `BLOCKED` with `GATE-HANDOFF-001` |
| Thermal climb | 5 | Verdict `BLOCKED` with `GATE-TEMP-004` and at least one passing remedy |
| Capacity loss between 30 and 60 per cent | 5 | Verdict depends on `scope` and not on any event name |
| Unseen event vector | 5 | Executes without error and satisfies monotonicity |

## 11. Prohibited constructions

| Prohibited | Detection |
|---|---|
| Comparison against an event name | Static scan; names permitted only under `research/scenarios/**` |
| Node, port, canal, or country names used as branch conditions | Static scan; names permitted only as data fields |
| Binary floating point in a decision path | Static scan of the decision modules |
| Verdict expressed as a number | Schema validation |
| Unlisted or malformed event input accepted silently | Schema validation; unknown input produces `BLOCKED` |

## 12. Limitations

1. The gate does not predict events.
2. The thermal model in pattern D2 is a hypothesis model without validation data. Any output
   that depends on it MUST state this limitation.
3. The gate certifies a plan against declared constraints. It does not certify product
   safety, regulatory compliance, or legal fitness for carriage.
4. Named scenarios exist as data for testing only, and MUST NOT be used as evidence of
   coverage of the event space.

