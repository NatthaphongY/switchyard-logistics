# Gate B4 measurement, generation two

Seed 20261023, 300 paired scenarios, intensity 1.0, elapsed 19.45 s, Python 3.13.3.

Ambient layer: on. Weather is priced into the consignment heat gain and the exceedance risk is read from the gate's own dose. Region table: measured, with provenance in the section below.

| Metric | Current practice | Generation one | Generation two |
|---|---|---|---|
| Unsafe control actions per scenario | 13.2167 | 11.6867 | 5.4033 |
| Blocking findings per scenario | 10.4967 | 8.9367 | 3.68 |
| Excursion minutes per scenario | 17.22 | 6.21 | 12.8133 |
| Thermal dose per delivered unit (permille) | 18.0608 | 7.9721 | 5.0753 |
| Quantity actually routed | 42.0667 | 40.64 | 41.8733 |
| Compliance spend, % of cargo value | 0.0036 | 0.0036 | 0.2236 |

## Paired effects

| Comparison | UCA reduction (pp, 95 % CI) | p (permutation) | Cliff's delta |
|---|---|---|---|
| gen1_vs_baseline | 11.58 (9.89 to 13.37) | 0.0001 | 0.1104 |
| gen2_vs_baseline | 59.12 (53.97 to 64.49) | 0.0001 | 0.6514 |
| gen2_vs_gen1 | 53.76 (48.43 to 59.21) | 0.0001 | 0.5614 |

Holdout (second half of the seeds, untouched by any tuning): UCA reduction 45.56 to 60.54 pp, p = 0.0001.

## Pre-registered criteria

| Criterion | Value | Operator | Limit | Passed |
|---|---|---|---|---|
| uca_ci_low_pp | 48.43 | ge | 15.0 | yes |
| blocks_not_worse | 5.256667 | ge | 0.0 | yes |
| service_floor_held | 1000.0 | ge | 950 | yes |
| cost_within_budget | 0.2236 | le | 0.5 | yes |
| dose_unit_not_worse_than_practice | 5.0753 | le | 18.0608 | yes |
| delivered_not_below_gen1 | 41.8733 | ge | 40.64 | yes |

Decision: **SEPARATES**.

## Ablation

_Ablation not requested._

## Ambient conditions and risk

| Comparator | Mean p(any exceedance) | Share with any dose | Mean peak dose (permille) | Peak dose, % of budget | Mean expected dose (permille) | Mean value at risk (currency) |
|---|---|---|---|---|---|---|
| baseline | 0.022318 | 0.03 | 67.263 | 6.726 | 15.257 | 1573.92 |
| gen1 | 0.012577 | 0.02 | 40.413 | 4.041 | 7.763 | 786.85 |
| gen2 | 0.011158 | 0.0267 | 23.2 | 2.32 | 5.173 | 881.32 |

Paired effect of pricing weather into the heat gain, gen2 on the same seeds: UCA -0.06 pp (-0.19 to 0.0); mean total thermal dose 24.837 to 32.193 permille (aggregate means, 29.62 %, positive = the forecast raised the dose); blocking findings delta -0.003333 (positive = weather raised them). The per-scenario paired change, averaged as a rate and signed as a reduction, is -30.76 %. The two percentages differ because one weights a scenario by its size and the other weights every scenario equally; both say the forecast raised the dose.

Region profiles: `measured`.

Profile provenance: ERA5 reanalysis via the Open-Meteo archive API (reanalysis climatology), month 7, period 1991-2020, retrieved 2026-10-23T00:04:03Z. Sites: R0 Frankfurt am Main, DE, R1 Guangzhou, CN, R2 Ulaanbaatar, MN. Licence: Open-Meteo data CC BY 4.0; ERA5 (C) Copernicus Climate Change Service, ECMWF. Attribution: Weather data by Open-Meteo.com (CC BY 4.0), derived from ERA5 reanalysis (Copernicus Climate Change Service).

Advisories raised by the weather layer (non-blocking by construction): WX-ADV-001 x1002, WX-ADV-002 x964, WX-ADV-003 x1042

Spread assumed for exceedance probability: sigma = 2.5 C forecast error, stated because the probability scales with it.

Budget the probability is measured against: 1000 permille of the thermal budget (the gate's own threshold). A probability of zero therefore reads as "no shipment came near the budget", not as "exposure was not measured" -- the share with any dose and the peak-dose-as-percentage columns are what make that distinction auditable.
