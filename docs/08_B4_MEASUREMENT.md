# SW-08 - Gate B4 measurement and verdict

| Field | Value |
|---|---|
| Document ID | SW-08 |
| Kind | Repository document (published) |
| Version | 2.1 |
| Status | Measured result; supersedes the generation-one measurement |
| Date | 2026-10-23 |
| Licence | Apache-2.0 |

Verdict: **SEPARATES**, on six criteria fixed before the run. Three planners, 300
paired scenarios, seed 20261023. Reproduce with
`scripts/run_b4.py --scenarios 300` (writes the evidence below);
the ablation in section 4 comes from `run_b4.py --scenarios 300 --ablation
--tag ABL`, which writes `evidence/B4_MEASUREMENT_V2_ABL.*` instead of
overwriting the headline file. Evidence: `evidence/B4_MEASUREMENT_V2.md` and
`.json`.

Two artefacts exist, and the difference between them is deliberate:

| Artefact | Command | Ambient layer |
|---|---|---|
| `B4_MEASUREMENT_V2.md` / `.json` | `run_b4.py --scenarios 300` | off: heat gain drawn by the scenario. This is the baseline the numbers below quote. |
| `B4_MEASUREMENT_V2_ABL.md` / `.json` | `run_b4.py --scenarios 300 --ablation --tag ABL` | off: the ablation ladder in section 4, kept in its own file |
| `B4_MEASUREMENT_V2_WX.md` / `.json` | `run_b4.py --scenarios 300 --weather --tag WX` | on: forecast built on the measured July climatology, priced into the heat gain, exceedance risk reported per planner |
| `B4_MEASUREMENT_V2_WXS.md` / `.json` | `run_b4.py --scenarios 300 --weather --weather-profile synthetic --tag WXS` | on, replaying the invented region table, so the numbers published before 2026-10-23 still reproduce |

The weather run is not a second headline. It answers a narrower question -- does
the verdict survive when ambient conditions, rather than a drawn heat gain, set
the thermal exposure -- and it does: same six criteria, same decision, thermal
dose per delivered unit 18.06 / 7.97 / 5.08 permille. Section 4.1 of SW-11
records the mechanism and the paired counterfactual that separates the cost of
the forecast from the effect of the planner.

The region table behind it is measured. `config/weather_regions.json` holds a
frozen July 1991-2020 climatology from ERA5 reanalysis, served free and keyless
by the Open-Meteo archive API, at three sites (Frankfurt am Main, Guangzhou,
Ulaanbaatar). The invented table the earlier run used is retained as the
`synthetic` profile: `--weather-profile synthetic` reproduces those numbers, and
`evidence/B4_MEASUREMENT_V2_WXS.*` is that replay. Attribution travels inside the
artefact because the licence requires it (CC BY 4.0).

Every artefact is reproducible byte for byte apart from the `elapsed_s` field:
two 300-scenario runs of the weather artefact were compared field by field and
differ only there (21.12 s against 23.51 s). `test_weather_run_is_reproducible_apart_from_the_clock`
holds that contract at five scenarios so a regression shows up in seconds.

## 1. What is compared

| Name | Planner | What it represents |
|---|---|---|
| current practice | `plan_greedy` | cost-first routing, capacity checked at booking, no compliance spend |
| generation one | `plan_priced` | congestion pricing, thermal awareness, slack reservation |
| generation two | `plan_remedied` | generation one plus every documented remedy and the physical layers |

The headline claim is generation two against generation one, because generation
one is already a competent planner. The comparison against practice is reported
as the operational number, and is labelled as such.

## 2. Measured result

| Metric | Practice | Generation one | Generation two |
|---|---|---|---|
| Unsafe control actions per scenario | 13.22 | 11.69 | 5.40 |
| Blocking findings per scenario | 10.50 | 8.94 | 3.68 |
| Thermal dose per delivered unit (permille) | 14.29 | 6.31 | 3.93 |
| Quantity routed | 42.07 | 40.64 | 41.87 |
| Compliance spend, percent of cargo value | 0.004 | 0.004 | 0.224 |

Paired effects, percentile bootstrap over 10,000 resamples with a sign-flip
permutation test:

| Comparison | UCA reduction (pp) | 95 percent CI | p | Cliff's delta |
|---|---|---|---|---|
| practice to generation one | 11.58 | 9.89 to 13.37 | 0.0001 | 0.11 |
| practice to generation two | 59.14 | 54.00 to 64.54 | 0.0001 | 0.65 |
| generation one to generation two | 53.79 | 48.43 to 59.21 | 0.0001 | 0.56 |

Holdout, second half of the seeds, never used for any tuning: 45.56 to 60.54 pp,
p = 0.0001. A result that only existed on the tuning half would be visible here.

## 3. Criteria, fixed before the run

| Criterion | Value | Limit | Passed |
|---|---|---|---|
| UCA reduction CI lower bound | 48.43 pp | at least 15 pp | yes |
| Blocking findings not worse | +5.26 fewer | at least 0 | yes |
| Service floor held in every scenario | 1000 permille | at least 950 | yes |
| Compliance spend | 0.224 percent of value | at most 0.5 percent | yes |
| Thermal dose per unit, non-inferior to practice | 3.93 | at most 14.29 | yes |
| Delivered quantity not below generation one | 41.87 | at least 40.64 | yes |

Two of these can fail the whole result and are not derived from the headline
number. The thermal criterion did fail on the first attempt (generation two was
11.6 percent worse per delivered unit); the planner was changed to buy active
cooling above a configured dose threshold, and the criterion was not relaxed.

## 4. Ablation, from real re-runs

Each row disables one remedy and re-plans all 300 scenarios.

| Remedy disabled | Mean UCA | Change |
|---|---|---|
| escrow | 8.867 | +3.467 |
| out-of-band document verification | 6.880 | +1.480 |
| backup mode | 6.227 | +0.827 |
| capacity measurement | 5.613 | +0.213 |
| feed refresh | 5.563 | +0.163 |
| pre-authorisation | 5.543 | +0.143 |
| active cooling | 5.417 | +0.017 |
| forward stock (pre-position) | 5.400 | +0.000 |

Forward stock contributes nothing in this corpus: the min-cut never binds below
demand for a consignment that also has stock available. The hook is kept, and
`tests/test_physical_gate_s.py` proves it works on a network where the cut does
bind, so the row is honest rather than decorative.

## 5. What is not claimed

- The 15 pp / 10 percent materiality thresholds from the earlier plan are still
  in `config/thresholds.json` as the pre-registered bar. The measured CI lower
  bound is far above it; the bar was not moved after seeing the result.
- No claim is made about a real corridor, product, or fleet. The scenarios are
  synthetic and seeded.
- A sentence claiming a fixed double-digit percentage-point reduction as the
  headline is a forbidden claim: the measured point estimate is larger, but such a
  sentence asserts a specific comparator and rounding that this report does not
  support. The prohibited wording is listed in the programme record, and a test
  fails if it reaches a published document.
