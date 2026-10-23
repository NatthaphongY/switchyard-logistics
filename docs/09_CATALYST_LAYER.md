# SW-09  -  Catalyst and Cascade Model

| Field | Value |
|---|---|
| Document ID | SW-09 |
| Kind | Repository document (published) |
| Version | 1.0 |
| Status | Normative for the scenario generator; informative for calibration |
| Date | 2026-10-23 |
| Related sections | Sections 2 to 6 of this document; SW-06 for the gate codes |
| Normative status | Axis definitions and formulas are binding on the generator; the numeric weights are programme decisions open to argument |

## 1. Why six axes are not enough

The six physical axes answer one question: how big is the shock, where, for how
long, and could it be seen coming. They do not answer why a routine bottleneck
becomes a system failure. That step needs propagation and institutions.

Three failure modes are invisible to a six-axis model.

1. A disruption that reproduces itself. A blocked lane pushes volume onto a
parallel lane, whose dwell rises, which breaks a handoff, which strands a
consignment at a node that then loses its slot. The second failure is not caused
by the storm; it is caused by the first failure.
2. A disruption that is not physical. A customs system that cannot verify a
document stops a truck that is running perfectly. A carrier that cannot pay for
fuel stops moving cargo without a single kilometre of road being damaged.
3. A disruption whose remedy is institutional. A permit, a solvency check, an
escrow, a union notice, a second mode. None of these is a route.

The programme therefore keeps the six axes as the physical layer and adds three
layers. Nothing in the gate reads an event name; every layer produces facts that
the gate can test.

## 2. Layer A, physical event, six axes

Unchanged from SW-06: `onset_rate`, `notice_min`, `duration`, `magnitude`,
`scope`, `reversibility`.

## 3. Layer B, propagation, four axes

| Axis | Admissible values | Unit | Mechanism | Gate consequence |
|---|---|---|---|---|
| `cascade_fanout` | 0.0 to 3.0 | mean secondary disruptions per active disruption | Branching process, imported from chain-reaction kinetics | None directly; produces the network the gate sees |
| `propagation_depth` | 1 to 4 | generations | Each generation is damped by 0.6 | Deeper cascades reduce the largest connected component |
| `repair_delay_min` | 120, 240, 480, 720 | minutes | Delayed restoration, imported from delayed-neutron kinetics: capacity returns late rather than never | A planner that holds a second option survives the delay; a fixed plan does not |
| `coupling` | derived | dimensionless | `susceptibility = (1 / (out_degree - 1)) x (1.15 - 0.3 x monitoring_coverage)` | Low redundancy and low monitoring raise the reproduction number |

The reproduction number is computed, not asserted:

    k_eff = cascade_fanout x susceptibility x (1 + catalyst_pressure)

`k_eff` below one decays; above one the cascade sustains itself. `k_eff` is
reported for every scenario, so a reader can see whether the scenario was
supercritical rather than taking the label on trust.

## 4. Layer C, information, two axes

| Axis | Admissible values | Mechanism | Gate consequence |
|---|---|---|---|
| `information_state` | verified, rumoured, contradictory, stale | What the planner knows about capacity and custody | `contradictory` clears the capacity verification flag (`GATE-DATA-002`); `stale` sets the input age above the freshness limit (`GATE-DATA-001`) |
| `measurement_uncertainty` | 0.02 to 0.15 | Relative uncertainty carried on the measurement | Recorded in the release; used for guard bands, not for silent rounding |

## 5. Layer D, actors and institutions, three axes

| Axis | Admissible values | Mechanism | Gate consequence |
|---|---|---|---|
| `actor_response` | cooperative, opportunistic, blocking | Opportunistic raises the price of a leg by 35 percent; blocking closes a lane for at least 240 minutes | Cost and route changes only; no new code |
| `contract_regime` | normal, force_majeure, penalty | Determines which remedies are admissible under the contract | Remedy vocabulary in SW-06 section 8 |
| `regulatory_gate` | none, permit, customs | Adds an approval step to the release | `GATE-PLAN-002` blocks a plan that needs approval when notice is zero |

## 6. Layer E, structural catalysts, four domains

A catalyst does not move cargo. It changes whether a local failure can spread.
Each domain carries measurable indices; the pressure term is their mean, so no
single domain can dominate by construction.

| Domain | Indices | Mechanism | Gate consequence |
|---|---|---|---|
| Geoeconomic fragmentation | `tariff_shock_pct` (0 to 0.35), `export_control` (boolean), `permit_lead_h` (24, 72, 168) | A cross-border lane becomes legally unusable or commercially irrational while remaining physically open | `GATE-LEGAL-001` blocks a cross-border leg when permits are not held |
| Workforce volatility | `vulnerability_index` (0.1 to 0.9), `action` (boolean), `notice_min` (0, 360, 1440) | A station loses throughput with no physical damage; dwell thresholds collapse to 30 percent of normal | `GATE-NODE-002` blocks a route through a station with no throughput |
| Credit and liquidity | `solvency_score` (0.15 to 0.95), `default` (boolean), `payment_terms_days` (30, 60, 90) | The operator stops moving cargo because it cannot fund the leg; the lane keeps its geometry and loses its capacity | `GATE-PARTY-001` blocks release while counterparty solvency is unverified |
| Cyber insecurity | `digital_dependency` (0.2 to 0.95), `intrusion` (boolean), `recovery_h` (12, 48, 120) | Documents and custody records cannot be verified, and monitoring is lost, while trucks still move | `GATE-HANDOFF-003` blocks release when custody records cannot be verified; monitoring loss raises `GATE-TEMP-003` |

Catalyst pressure is the mean of four normalised values:

    pressure = mean(
        1 if export_control else tariff_shock_pct / 0.35,
        1 if labour action else vulnerability_index,
        1 if payment default else 1 - solvency_score,
        1 if intrusion else 0.5 x digital_dependency
    )

then

    k_eff = cascade_fanout x susceptibility x (1 + pressure)

The last term is the point of the layer. A catalyst does not add a disruption; it
multiplies the reproduction number of the disruptions already present. An open
border, a solvent carrier, verified documents and no ransomware put pressure near
zero, and the same disruption stays local.

## 7. Percolation check

After the cascade the generator measures the largest connected component of the
ambient and cold-chain eligible graphs. A network that still moves slowly keeps
one component; a network that has fragmented loses it. The figure is reported per
scenario, because a capacity number alone cannot distinguish congestion from
severance.

## 8. Mapping summary

| Layer | Axes | Adds to the gate |
|---|---|---|
| A physical | 6 | Nothing new; sets the magnitude |
| B propagation | 4 | Nothing directly; shapes the network the gate tests |
| C information | 2 | `GATE-DATA-001`, `GATE-DATA-002` |
| D institutions | 3 | `GATE-PLAN-002` |
| E catalysts | 4 domains, 12 indices | `GATE-LEGAL-001`, `GATE-NODE-002`, `GATE-PARTY-001`, `GATE-HANDOFF-003` |

The gate stays event-agnostic: it tests a plan against a network and a set of
verified facts. No code path branches on a catalyst name; the names live in the
generator and in this document.

## 9. Evidence status and limits

The four catalyst domains were specified with reference to global
risk reporting. Retrieval of those external publications from this environment
failed (HTTP 403, HTTP 404, and one document above the size limit), so this
document records no ranking, percentage, or quotation from them. Nothing in the
model depends on such a figure: the indices are programme definitions with stated
ranges, and the pressure weights are programme decisions.

Stated limits, so that no reader mistakes the model for a calibrated estimate:

1. `k_eff` is computed from synthetic topology. It is not an empirical estimate
   for any port, corridor, or carrier.
2. The damping factor 0.6 and the 45 percent capacity loss per secondary hit are
   design choices, not measurements.
3. Financial, labour, and cyber effects are represented as capacity, throughput,
   price, and verification flags. They are not models of those systems.
4. The generator produces the same bytes from the same seed, which is what the
   conformance gate needs. Reproducibility is not validity.

