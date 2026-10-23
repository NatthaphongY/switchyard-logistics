# Gate B4 measurement, generation two

Seed 20261023, 300 paired scenarios, intensity 1.0, elapsed 42.51 s, Python 3.13.3.

Ambient layer: off. Heat gain is drawn directly by the scenario, so these numbers are the published baseline.

| Metric | Current practice | Generation one | Generation two |
|---|---|---|---|
| Unsafe control actions per scenario | 13.2167 | 11.6867 | 5.4 |
| Blocking findings per scenario | 10.4967 | 8.9367 | 3.6767 |
| Excursion minutes per scenario | 17.22 | 6.21 | 12.8133 |
| Thermal dose per delivered unit (permille) | 14.2936 | 6.3089 | 3.9335 |
| Quantity actually routed | 42.0667 | 40.64 | 41.8733 |
| Compliance spend, % of cargo value | 0.0036 | 0.0036 | 0.2236 |

## Paired effects

| Comparison | UCA reduction (pp, 95 % CI) | p (permutation) | Cliff's delta |
|---|---|---|---|
| gen1_vs_baseline | 11.58 (9.89 to 13.37) | 0.0001 | 0.1104 |
| gen2_vs_baseline | 59.14 (54.0 to 64.54) | 0.0001 | 0.6517 |
| gen2_vs_gen1 | 53.79 (48.43 to 59.21) | 0.0001 | 0.5619 |

Holdout (second half of the seeds, untouched by any tuning): UCA reduction 45.56 to 60.54 pp, p = 0.0001.

## Pre-registered criteria

| Criterion | Value | Operator | Limit | Passed |
|---|---|---|---|---|
| uca_ci_low_pp | 48.43 | ge | 15.0 | yes |
| blocks_not_worse | 5.26 | ge | 0.0 | yes |
| service_floor_held | 1000.0 | ge | 950 | yes |
| cost_within_budget | 0.2236 | le | 0.5 | yes |
| dose_unit_not_worse_than_practice | 3.9335 | le | 14.2936 | yes |
| delivered_not_below_gen1 | 41.8733 | ge | 40.64 | yes |

Decision: **SEPARATES**.

## Ablation

| Remedy disabled | Mean UCA | Change versus full reference |
|---|---|---|
| escrow | 8.867 | +3.467 |
| out_of_band_verify | 6.88 | +1.48 |
| backup_mode | 6.227 | +0.827 |
| capacity_measure | 5.613 | +0.213 |
| refresh_feed | 5.563 | +0.163 |
| pre_authorisation | 5.543 | +0.143 |
| active_cooling | 5.417 | +0.017 |
| preposition | 5.4 | +0.0 |

## Ambient conditions and risk

_Weather layer not requested (`--weather`)._

