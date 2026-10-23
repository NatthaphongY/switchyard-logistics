"""Risk and probability features (BHR-RS-14).

The gate answers pass or block. A paper needs a probability and a tail. Two
layers, deliberately kept apart:

  * `thermal_exceedance` -- analytic, closed form. It consumes the dose the gate
    already measured, so there is one definition of thermal exposure in the
    programme and this module cannot drift from it.
  * `crps_ensemble` / `brier` / `reliability_table` -- empirical scorers for a
    deterministic parametric ensemble. They measure whether the analytic layer
    agrees with the sampler. They are not evidence that either agrees with the
    field, and BHR-RS-14 says so in the limitations.
"""

from __future__ import annotations

import math
from statistics import fmean
from typing import Dict, Iterable, List, Sequence, Tuple

from . import weather
from .gate import Release
from .model import Consignment, Network, Plan
from .physics import expected_shortfall

PERMILLE = 1000


def normal_cdf(z: float) -> float:
    """Standard normal CDF from the error function (stdlib, no SciPy)."""
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def relative_sigma(
    temp_class: str, sigma_c: float = 2.5, sensitivity_permille: Dict[str, int] = None
) -> float:
    """Turn a forecast spread in degrees into a relative spread on the dose.

    The heat multiplier rises by `class_sensitivity_permille` for every tenth of
    a degree above the class band, so `sigma_c` degrees become

        rel_sigma = sigma_c * 10 tenths * (sensitivity / 1000)

    of the dose. A frozen consignment is more weather-sensitive than an ambient
    one; that is the whole point of the class table.
    """
    table = sensitivity_permille or weather.config()["class_sensitivity_permille"]
    return max(0.0, sigma_c) * 10.0 * (table[temp_class] / PERMILLE) / 100.0


def _exceedance_probability(dose_permille: int, threshold_permille: int, spread: float) -> float:
    """Three regimes, written as guards rather than a ladder.

    Zero dose never fails; zero spread makes the outcome deterministic; otherwise
    the gap is expressed as a ratio so the integral is scale free.
    """
    if dose_permille <= 0:
        return 0.0
    if spread <= 0.0:
        return 1.0 if dose_permille > threshold_permille else 0.0
    return 1.0 - normal_cdf(((threshold_permille / dose_permille) - 1.0) / spread)


def thermal_exceedance(
    consignment: Consignment,
    dose_permille: int,
    report: weather.WeatherReport,
    threshold_permille: int = PERMILLE,
    sigma_c: float = 2.5,
) -> dict:
    """P(thermal dose > budget) for one consignment given a measured dose.

    `dose_permille` is `Release.thermal_dose[cid]` -- the gate's own number, with
    weather already priced into the heat gain. The only input from outside is
    `sigma_c`, the forecast spread; a paper must state it and show the result's
    sensitivity to it.

    With dose 0 the answer is 0: cargo that is not exposed has no thermal
    exceedance risk. With dose above budget the answer is above one half, which
    is the honest reading of an already-failing shipment rather than a clamp to 1.
    """
    spread = relative_sigma(consignment.temp_class, sigma_c)
    dose = max(0, int(dose_permille))
    gap = report.degrees_above_band[consignment.temp_class] / 10.0
    probability = _exceedance_probability(dose, threshold_permille, spread)
    probability = min(1.0, max(0.0, probability))
    value = consignment.value_usd
    return {
        "consignment": consignment.id,
        "temp_class": consignment.temp_class,
        "band_gap_c": round(gap, 3),
        "dose_permille": dose,
        "headroom_permille": threshold_permille - dose,
        "relative_sigma": round(spread, 4),
        "p_exceedance": round(probability, 6),
        "value_usd": value,
        "value_at_risk_usd": round(probability * value, 4),
    }


def portfolio(
    network: Network,
    plan: Plan,
    release: Release,
    report: weather.WeatherReport,
    sigma_c: float = 2.5,
    threshold_permille: int = PERMILLE,
) -> dict:
    """Roll per-consignment exceedance up to one number a risk officer can use.

    Independent-consignment assumption: p_any = 1 - product(1 - p). Stated
    plainly because weather is spatially correlated and the product therefore
    understates joint failure. The dependency correction is BHR-RS-14 section 6.

    `plan` is accepted and reported (`strategy`) but not re-derived: the dose came
    from a gate run of that plan, and recomputing it here would create a second
    definition of exposure -- the exact failure this module exists to avoid.
    """
    protected = frozenset(plan.thermal_protection)
    rows = [
        thermal_exceedance(
            consignment,
            release.thermal_dose.get(consignment.id, 0),
            report,
            threshold_permille=threshold_permille,
            sigma_c=sigma_c,
        )
        | {"protected": consignment.id in protected}
        for consignment in network.consignments
    ]
    survival = 1.0
    for row in rows:
        survival *= 1.0 - row["p_exceedance"]
    weights = [row["value_usd"] for row in rows]
    total_weight = sum(weights)
    expected_dose = (
        int(round(sum(w * row["dose_permille"] for w, row in zip(weights, rows)) / total_weight))
        if total_weight > 0 and rows
        else (int(round(fmean(row["dose_permille"] for row in rows))) if rows else 0)
    )
    return {
        "scenario": network.name,
        "strategy": plan.strategy,
        "verdict": release.verdict,
        "sigma_c": sigma_c,
        "threshold_permille": threshold_permille,
        "p_any_exceedance": round(1.0 - survival, 6),
        "max_p_exceedance": max((row["p_exceedance"] for row in rows), default=0.0),
        "max_dose_permille": max((row["dose_permille"] for row in rows), default=0),
        "expected_dose_permille": expected_dose,
        "value_at_risk_usd": round(sum(row["value_at_risk_usd"] for row in rows), 2),
        "rows": rows,
    }


def crps_ensemble(observation: float, members: Sequence[float]) -> float:
    """Fair CRPS for an ensemble forecast of a scalar (Gneiting et al.).

    The fair estimator uses m(m-1) in the spread term so a small ensemble is not
    rewarded for being small. Lower is better; 0 means the ensemble is the truth.
    """
    count = len(members)
    if count == 0:
        return float("nan")
    if count == 1:
        return abs(members[0] - observation)
    first = fmean(abs(member - observation) for member in members)
    spread = sum(
        abs(members[i] - members[j]) for i in range(count) for j in range(i + 1, count)
    )
    return first - 2.0 * spread / (count * (count - 1))


def brier(probability: float, outcome: bool) -> float:
    """Brier score: squared error of a probability forecast. Lower is better."""
    return (probability - (1.0 if outcome else 0.0)) ** 2


def quantile(values: Iterable[float], q: float) -> float:
    """Linear-interpolated quantile; `q` in [0, 1]."""
    ordered = sorted(values)
    if not ordered:
        return float("nan")
    position = min(1.0, max(0.0, q)) * (len(ordered) - 1)
    low = int(math.floor(position))
    high = min(low + 1, len(ordered) - 1)
    weight = position - low
    return ordered[low] * (1.0 - weight) + ordered[high] * weight


def reliability_table(
    rows: Sequence[Tuple[float, bool]],
    edges: Sequence[float] = (0.0, 0.2, 0.4, 0.6, 0.8, 1.0),
) -> List[dict]:
    """Bin (probability, outcome) pairs and report forecast against observed.

    A calibration claim needs this table with a sample large enough to fill the
    bins. The runner prints the counts so an empty bin is visible, not implied.
    """
    table: List[dict] = []
    last = len(edges) - 2
    for index in range(len(edges) - 1):
        low, high = edges[index], edges[index + 1]
        bucket = [
            (probability, outcome)
            for probability, outcome in rows
            if low <= probability < high or (index == last and probability == high)
        ]
        count = len(bucket)
        table.append(
            {
                "bin": f"[{low:.1f},{high:.1f})",
                "count": count,
                "forecast_mean": round(fmean(p for p, _ in bucket), 4) if count else None,
                "observed_rate": (
                    round(fmean(1.0 if outcome else 0.0 for _, outcome in bucket), 4)
                    if count
                    else None
                ),
            }
        )
    return table


def tail(values: Sequence[float], alpha: float = 0.95) -> Dict[str, float]:
    """Mean, p95 and expected shortfall for a sample (reuses the physics tail)."""
    if not values:
        return {"mean": 0.0, "p95": 0.0, "expected_shortfall": 0.0}
    return {
        "mean": round(fmean(values), 4),
        "p95": round(quantile(values, 0.95), 4),
        "expected_shortfall": round(expected_shortfall(list(values), alpha), 4),
    }

