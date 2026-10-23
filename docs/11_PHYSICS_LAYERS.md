# BHR-RS-11 - Physical layers

| Field | Value |
|---|---|
| Document ID | BHR-RS-11 |
| Version | 1.1 |
| Status | Active; adopted layers and their limits |
| Date | 2026-10-23 |
| Licence | Apache-2.0 |

Purpose: the gate is not allowed to be a checklist of things that feel risky. Each
extra rule has to come from a field that already solved the same structural
problem, and has to be stated with its domain of validity. This document records
what was adopted, what was rejected, and what each layer changed in the measured
result.

## 1. Survey: what was considered

| Field | Mechanism | Verdict |
|---|---|---|
| Nuclear engineering | Branching process, k_eff | Adopted earlier (`cascade.py`) |
| Statistical physics | Percolation, giant component | Adopted earlier (`cascade.py`) |
| Reactor kinetics | Delayed response after shutdown | Adopted earlier (`cascade.py`) |
| Queueing theory | Kingman / Allen-Cunneen, utilisation collapse | Adopted, `GATE-QUEUE-001` |
| Traffic flow | LWR kinematic wave, triangular fundamental diagram | Adopted for scoring and delay reporting |
| Heat transfer | Newton cooling, thermal mass | Adopted, drives the dose model |
| Reaction kinetics | Arrhenius, mean kinetic temperature | Adopted as the reference the linear bound must beat |
| Reliability theory | Series and parallel availability | Adopted, `GATE-RELIAB-001` |
| Epidemiology | SIR final size, herd immunity threshold | Adopted as an analytic check on cascade saturation |
| Finance | Expected shortfall (CVaR) | Adopted as a reported endpoint |
| Control theory | Dead time, loop gain, stability margin | Rejected: the planner is open loop by design |
| Electrochemistry | Battery state of health for reefer units | Rejected: no unit-level data |
| Hydrology | Reservoir routing, spillway curves | Rejected: same mathematics as queueing |
| Acoustics | Sound propagation | Rejected: no decision depends on it |
| Game theory | Adversarial inspector / shipper equilibrium | Noted, not built: needs a payoff model |

The survey is deliberately wider than the implementation. A field is only adopted
when it changes a decision; otherwise it is a paragraph in a report, and reports
are cheaper than code.

## 2. Queueing: why utilisation is a gate rule

Demand below capacity is not safety. At utilisation rho the expected wait grows
like rho^(sqrt(2(c+1))-1) / (c(1-rho)); the last five percent of capacity costs
more delay than the first eighty. A gate that compares throughput with demand
therefore passes the plan that is about to stall.

Implementation: `utilisation_permille()` and a delay-factor table, both integer.
The table exists because the decision path is not allowed to evaluate a power or
an exponential: those are the operations that make two languages disagree.

Check: `tests/test_physics_layers_s.py` pins the M/M/1 reduction and the
monotonicity; `tests/test_physical_gate_s.py` pins the finding.

## 3. Traffic flow: why delay is a function of density

Under the triangular fundamental diagram, a lane carries `capacity` at
intermediate density and collapses to zero at jam density. Travel time therefore
depends on density, not only on distance. The model is used to price congestion
when ranking candidate paths and to report expected delay; it does not decide
release, because the gate cannot observe density.

## 4. Heat and kinetics: why minutes are not a safety metric

Two consignments with the same excursion minutes can lose very different
fractions of potency. Newton cooling gives the temperature curve; Arrhenius gives
the relative degradation rate; mean kinetic temperature gives the single number a
pharmacist recognises.

The gate uses a linear dose in per-mille of a quality budget. That is a
conservative stand-in, and conservativeness is a test, not a promise:
`test_linear_bound_is_conservative_against_kinetics` fails if the linear bound
ever under-reports the kinetic estimate.

Measured effect: thermal dose per delivered unit fell from 14.29 permille
(current practice) and 6.31 (generation one) to 3.93 (generation two), with the
ablation showing that the gain comes from route choice, not from cooling spend
(disabling `active_cooling` changes mean unsafe actions by +0.017).

### 4.1 Ambient conditions: a re-pricing, not a new rule

`weather.py` turns the scenario seed into a per-region forecast: peak temperature
in tenths of a degree, storm index, humidity and solar load in per-mille. Every
field is an integer, so the report is a pure function of the seed and the Rust
replay sees the same numbers (`test_weather_report_is_a_pure_function_of_the_seed`).

The region table is measured, not invented. `research/config/weather_regions.json`
holds a frozen July climatology for 1991 to 2020, derived from ERA5 reanalysis
served by the free, keyless Open-Meteo archive API, at three sites that stand for
the three climate classes the scenario generator emits: Frankfurt am Main for
temperate maritime, Guangzhou for humid subtropical, Ulaanbaatar for continental
interior. Base temperature, diurnal swing, humidity, solar load and wet-day share
are all derived by integer arithmetic from daily aggregates, and the derivation is
tested against a hand-computed series (`tests/test_weather_regions_s.py`). The
invented table is retained as the `synthetic` profile, because the evidence
published before the swap has to replay: `--weather-profile synthetic` reproduces
those numbers, and `evidence/B4_MEASUREMENT_V2_WXS.*` is the replay that proves it.

The layer enters the system at exactly one place: it multiplies each
consignment's `heat_gain_permille` (`weather.apply`). Nothing else changes --
the planners, the evaluator and the gate keep their existing inputs, and the
conformance core never receives weather at all, only the re-priced heat gain.
That is why pricing ambient conditions cannot break bit-for-bit parity.

Exceedance risk (`risk.py`) is then read from the gate's own dose, not recomputed:
a second definition of exposure is the failure mode this programme exists to
avoid. Probability is a normal CDF over the ratio of budget to measured dose with
the forecast spread passed in explicitly (`sigma_c`, 2.5 degrees by default), and
p(any) is the independence product across consignments -- which understates joint
failure, because weather is spatially correlated. Both assumptions are printed in
the report next to the numbers rather than left in a docstring.

Measured with the layer on (300 paired scenarios, seed 20261023,
`evidence/B4_MEASUREMENT_V2_WX.md`, decision still SEPARATES):
| Endpoint | Current practice | Generation one | Generation two |
|---|---|---|---|
| Mean p(any exceedance) | 0.0223 | 0.0126 | 0.0112 |
| Share of scenarios with any dose | 0.030 | 0.020 | 0.027 |
| Peak dose, percent of budget | 6.73 | 4.04 | 2.32 |
| Mean value at risk (currency) | 1573.92 | 786.85 | 881.32 |
| Thermal dose per delivered unit (permille) | 18.06 | 7.97 | 5.08 |

The paired counterfactual (generation two re-planned on the un-priced network,
same seeds) separates the two effects that a single run would conflate: pricing
the forecast raises mean total thermal dose from 24.84 to 32.19 permille
(+29.6 percent, i.e. ambient conditions add exposure that the synthetic scenario
previously hid) while unsafe control actions move by -0.06 pp (95 percent CI
-0.19 to 0.00) and blocking findings by -0.003. Weather is therefore not a free
win and not a penalty: it makes an existing exposure visible, and the planner
absorbs it at roughly unchanged compliance.

Advisories (`WX-ADV-001..003`, 1002 / 964 / 1042 hits in this run) are advice
only. `test_advisories_never_block_a_release` fails if an advisory ever reaches
`blocks` or changes a verdict, so the layer can inform an operator without
silently moving the gate.

The replay runs in both directions. Running the same 300 scenarios against the
retained invented table (`--weather-profile synthetic`,
`evidence/B4_MEASUREMENT_V2_WXS.md`) reproduces the pre-swap result exactly:
0.0224 / 0.0127 / 0.0112 p(any), 17.96 / 8.03 / 5.10 permille per delivered unit,
and 1011 / 158 / 1042 advisories. The two runs therefore differ only in the
region table. What the measured table changes is the advisory mix: storm overlap
(`WX-ADV-002`) rises from 158 to 964 hits, because Guangzhou is wet on 727
per-mille of its July days against a 350 per-mille threshold, where the invented
table claimed 420. The placeholder understated storm exposure and slightly
flattered the thermal result.

## 5. Reliability: why long routes fail more often than intuition

A route is a series system: availability is the product of the per-mode
availabilities. Five road legs at 0.993 each leave 0.965; eight legs leave 0.945.
A booked backup mode turns the weakest link into a parallel pair, and that is
exactly what the gate's remedy text already demanded ("hold capacity on a second
mode"). The rule and the remedy now agree.

## 6. Epidemiology: an analytic check, not a metaphor

A cascade and an outbreak share the same saturation equation. The final size of a
simple SIR outbreak solves `s = exp(-R0 (1 - s))`, which depends on R0 alone.
That gives a closed-form sanity check on the simulated cascade: if the simulated
final size drifts far from the analytic value, the simulation is wrong.

Herd-immunity threshold `1 - 1/R0` is reported alongside, because it is the point
at which a cascade stops being able to sustain itself: repair capacity above that
share ends a cascade, below it the cascade runs to saturation.

## 7. Finance: why the tail is reported

A planner can look good by improving the easy half of the distribution. The B4
report therefore carries expected shortfall at 95 percent alongside the mean, and
the per-unit thermal dose, so that moving cargo into a bad tail is visible.

## 8. Limits, stated

- Every constant in `config/physics.json` is a programme assumption for a
  synthetic network. None is an empirical estimate for a named corridor, product,
  or fleet.
- Queue delays use a table, so the gate is a bounded approximation of the
  analytic form. The analytic form is in the same module and is tested; the table
  is what the two languages can agree on bit for bit.
- Heat gain per consignment is drawn, not measured. The layer fixes the shape of
  the trade-off (exposure against budget), not the magnitude for a real product.
- The ambient layer re-prices that drawn heat gain from a seeded forecast built on
  a frozen July climatology, not a live forecast and not a full year. Three sites
  stand for the regions a scenario can name, so the layer is a statement about the
  mechanism (ambient conditions raise exposure and are absorbed by route choice)
  plus a checkable order of magnitude, not a route survey. The forecast spread used
  for exceedance probability is an assumption (2.5 degrees), printed with the
  result because the probability scales with it.
- No field was adopted to make the numbers larger. The criteria that could have
  failed were fixed before the run; one of them, thermal non-inferiority, did
  fail on the first attempt, and the planner was changed rather than the
  criterion.
