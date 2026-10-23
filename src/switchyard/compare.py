"""Gate B4 comparison: three planners, pre-registered criteria, honest guards.

What is measured, and why each comparator exists:

  * baseline (generation zero) -- current practice: cost-first routing, capacity
    checked only at booking time, no compliance spend;
  * generation one -- the previous reference planner: congestion pricing, thermal
    awareness, slack reservation. This is the *standard comparator*, so the
    published effect is not measured against a straw man;
  * generation two -- generation one plus every documented remedy, and plus the
    physical layers (queue, thermal dose, reliability, service floor).

The reported claim is gen2 versus gen1: an incremental result on top of a
competent planner. Baseline comparisons are reported too, because the owner asked
for the operational number, but they are labelled as such.

Guards, all pre-registered in config/thresholds.json:

  * blocking findings must not increase;
  * the deliberate deferral floor must hold in every scenario;
  * compliance spend must stay under a stated share of cargo value.

If any guard fails the decision is REGRESSION regardless of the headline effect.
"""

from __future__ import annotations

import statistics
import time
from typing import Dict, List, Optional, Sequence

from . import risk, weather
from .evaluate import prepare
from .gate import evaluate
from .model import Network, Plan, Thresholds
from .planners import plan_cost, plan_greedy, plan_priced, plan_remedied
from .scenarios import scenario
from .stats import cliffs_delta, holdout_split, summarise_differences

COMPARATORS = ("baseline", "gen1", "gen2")

# Planner registry: adding a comparator is adding a row, not adding a branch.
PLANNER_REGISTRY = {
    "baseline": lambda network, thresholds, event: plan_greedy(network, thresholds),
    "gen1": lambda network, thresholds, event: plan_priced(
        network, thresholds, event=event
    )[0],
    "gen2": lambda network, thresholds, event: plan_remedied(
        network, thresholds, event=event
    ),
}
# Remedy groups used for the ablation. Disabling a group is a real re-run, not a
# post-hoc subtraction of counts.
ABLATION_GROUPS = (
    "escrow",
    "pre_authorisation",
    "refresh_feed",
    "capacity_measure",
    "out_of_band_verify",
    "active_cooling",
    "preposition",
    "backup_mode",
)


def _plan_for(name: str, network: Network, thresholds: Thresholds, event: dict) -> Plan:
    return PLANNER_REGISTRY[name](network, thresholds, event)


def _measure(
    network: Network,
    event: dict,
    plan: Plan,
    thresholds: Thresholds,
    report: Optional["weather.WeatherReport"] = None,
) -> Dict[str, float]:
    prepared = prepare(plan, event)
    release = evaluate(network, prepared, event, thresholds)
    cost = plan_cost(network, prepared)
    value = sum(c.value_usd for c in network.consignments) or 1.0
    routed = [c for c in network.consignments if prepared.legs_of(c.id)]
    routed_qty = sum(c.qty for c in routed) or 1.0
    dose_unit = sum(
        release.thermal_dose.get(c.id, 0) * c.qty for c in routed
    ) / routed_qty
    row = {
        "uca": float(release.unsafe_control_actions),
        "blocks": float(release.blocks),
        "excursion": float(release.excursion_total),
        "dose": float(sum(release.thermal_dose.values())),
        "dose_unit": float(dose_unit),
        "routed_qty": float(sum(c.qty for c in routed)),
        "over_budget": float(
            sum(1 for value_ in release.thermal_dose.values() if value_ > thresholds.thermal_budget_permille)
        ),
        "served": float(release.served),
        "cost": cost,
        "cost_pct_value": 100.0 * cost / value,
        "compliance_pct_value": 100.0 * (cost - sum(
            network.consignment(leg.consignment).qty * network.lane(leg.lane).cost_per_unit
            for leg in prepared.legs
        )) / value,
    }
    if report is not None:
        # Threshold is the gate's own thermal budget, not the module default:
        # a caller may move the budget, and the risk column must move with it.
        book = risk.portfolio(
            network,
            prepared,
            release,
            report,
            threshold_permille=thresholds.thermal_budget_permille,
        )
        row["p_exceedance"] = book["p_any_exceedance"]
        row["max_dose_permille"] = float(book["max_dose_permille"])
        row["dose_expected"] = float(book["expected_dose_permille"])
        row["value_at_risk"] = book["value_at_risk_usd"]
        # Where the worst shipment sits relative to the gate's budget. A
        # probability near zero is only meaningful with this distance beside it.
        row["dose_pct_budget"] = round(
            100.0 * book["max_dose_permille"] / max(1, thresholds.thermal_budget_permille), 3
        )
    return row


def run_comparison(
    scenarios: int = 300,
    seed: int = 20261023,
    intensity: float = 1.0,
    thresholds: Optional[Thresholds] = None,
    ablation: bool = False,
    weather_layer: bool = False,
    weather_profile: Optional[str] = None,
) -> Dict[str, object]:
    """Run the three comparators over paired scenarios.

    `weather_layer` re-prices each consignment's heat gain from the same event
    vector before any planner runs, and adds the risk columns. The counterfactual
    (gen2 on the un-priced network) is measured on the same seed, so the report
    can state what the weather-aware price changed instead of asserting it.
    `weather_profile` selects the region table: `measured` is the open
    reanalysis climatology, `synthetic` replays the earlier evidence.
    """
    thresholds = thresholds or Thresholds()
    rows: Dict[str, List[Dict[str, float]]] = {name: [] for name in COMPARATORS}
    counterfactual: List[Dict[str, float]] = []
    advisory_counts: Dict[str, int] = {}
    started = time.perf_counter()
    hashes: List[str] = []
    for index in range(scenarios):
        network, event = scenario(seed + index, intensity=intensity)
        report = (
            weather.assess(
                event,
                seed=seed + index,
                intensity=intensity,
                profile=weather_profile,
            )
            if weather_layer
            else None
        )
        priced = weather.apply(network, report) if report is not None else network
        plans = {name: _plan_for(name, priced, thresholds, event) for name in COMPARATORS}
        for name in COMPARATORS:
            rows[name].append(_measure(priced, event, plans[name], thresholds, report))
        if report is not None:
            counterfactual.append(
                _measure(network, event, _plan_for("gen2", network, thresholds, event), thresholds)
            )
            for finding in weather.findings(priced, plans["gen2"], report):
                advisory_counts[finding["code"]] = advisory_counts.get(finding["code"], 0) + 1
        if index == 0:
            hashes.append(
                evaluate(network, prepare(plan_remedied(network, thresholds, event=event), event), event, thresholds).hash
            )

    ablation_rows: Dict[str, List[Dict[str, float]]] = {}
    if ablation:
        for group in ABLATION_GROUPS:
            series: List[Dict[str, float]] = []
            for index in range(scenarios):
                network, event = scenario(seed + index, intensity=intensity)
                plan = plan_remedied(network, thresholds, event=event, disable=(group,))
                series.append(_measure(network, event, plan, thresholds))
            ablation_rows[group] = series

    return {
        "scenarios": scenarios,
        "seed": seed,
        "intensity": intensity,
        "elapsed_s": round(time.perf_counter() - started, 2),
        "rows": rows,
        "ablation": ablation_rows,
        "first_hash": hashes[0] if hashes else "",
        "weather": {
            "layer": bool(weather_layer),
            "profile": weather.active_profile(weather_profile) if weather_layer else None,
            "profile_source": weather.source(weather_profile) if weather_layer else None,
            "counterfactual": counterfactual,
            "advisory_counts": dict(sorted(advisory_counts.items())),
            "budget_permille": thresholds.thermal_budget_permille,
        },
    }


def _effect(before: Sequence[Dict[str, float]], after: Sequence[Dict[str, float]]) -> Dict[str, object]:
    """Paired effect of `after` relative to `before` on every endpoint."""
    uca_delta = [b["uca"] - a["uca"] for b, a in zip(before, after)]
    dose_relative = [
        (b["dose"] - a["dose"]) / b["dose"] for b, a in zip(before, after) if b["dose"] > 0
    ]
    blocks_delta = [b["blocks"] - a["blocks"] for b, a in zip(before, after)]
    uca_stats = summarise_differences(uca_delta)
    dose_stats = summarise_differences(dose_relative)
    return {
        "uca_delta": uca_stats,
        "uca_reduction_pp": round(100.0 * uca_stats["mean"] / max(statistics.fmean([b["uca"] for b in before]), 1.0), 2),
        "uca_reduction_pp_ci95": [
            round(100.0 * uca_stats["ci_low"] / max(statistics.fmean([b["uca"] for b in before]), 1.0), 2),
            round(100.0 * uca_stats["ci_high"] / max(statistics.fmean([b["uca"] for b in before]), 1.0), 2),
        ],
        "dose_reduction_pct": round(100.0 * dose_stats["mean"], 2),
        "dose_reduction_pct_ci95": [
            round(100.0 * dose_stats["ci_low"], 2),
            round(100.0 * dose_stats["ci_high"], 2),
        ],
        "blocks_delta": summarise_differences(blocks_delta),
        "cliffs_delta_uca": round(cliffs_delta([b["uca"] for b in before], [a["uca"] for a in after]), 4),
    }


def _means(rows: Sequence[Dict[str, float]]) -> Dict[str, float]:
    keys = rows[0].keys() if rows else ()
    return {key: round(statistics.fmean(row[key] for row in rows), 4) for key in keys}


# Pre-registered acceptance criteria. `op` reads from the same comparator table
# the gate uses, so "greater than or equal" means one thing in this programme.
CRITERIA = (
    ("uca_ci_low_pp", "uca_ci_low_pp", "ge", "materiality_uca_points", True),
    ("blocks_not_worse", "blocks_delta_mean", "ge", "zero", True),
    ("service_floor_held", "min_served", "ge", "service_floor_permille", True),
    ("cost_within_budget", "compliance_pct_value", "le", "cost_budget_pct_of_value", True),
    ("dose_unit_not_worse_than_practice", "dose_unit", "le", "dose_unit_baseline", True),
    ("delivered_not_below_gen1", "routed_qty", "ge", "routed_qty_gen1", True),
)
CONSTANT_LIMITS = {"zero": 0.0}


def _weather_summary(
    result: Dict[str, object], rows: Dict[str, List[Dict[str, float]]]
) -> Dict[str, object]:
    """Roll the weather layer up for the report.

    `panel` is the risk book per comparator (weather priced in). `counterfactual`
    is gen2 on the un-priced network for the same seeds, so the paired effect is a
    measurement rather than a claim: positive numbers mean the weather-aware price
    changed the decision, and the sign says in which direction.
    """
    book = result.get("weather") or {}
    if not book.get("layer"):
        return {"layer": False}
    panel = {
        name: {
            "p_any_exceedance": round(statistics.fmean(r["p_exceedance"] for r in rows[name]), 6),
            "max_dose_permille": round(statistics.fmean(r["max_dose_permille"] for r in rows[name]), 3),
            "expected_dose_permille": round(statistics.fmean(r["dose_expected"] for r in rows[name]), 3),
            "value_at_risk_usd": round(statistics.fmean(r["value_at_risk"] for r in rows[name]), 2),
            # Disclosure: exposure is concentrated. A near-zero mean probability is
            # only informative next to the share of scenarios that had any dose at
            # all, otherwise a reader cannot tell "safe" from "never measured".
            "share_dose_positive": round(
                statistics.fmean(1.0 if r["max_dose_permille"] > 0 else 0.0 for r in rows[name]), 4
            ),
            # Distance from the budget, so a near-zero probability cannot be read
            # as "no exposure was measured".
            "mean_dose_pct_budget": round(
                statistics.fmean(r["dose_pct_budget"] for r in rows[name]), 3
            ),
        }
        for name in COMPARATORS
        if rows[name] and "p_exceedance" in rows[name][0]
    }
    counterfactual = book.get("counterfactual") or []
    paired = None
    if counterfactual and len(counterfactual) == len(rows["gen2"]):
        paired = _effect(counterfactual, rows["gen2"])
        # The paired relative change is per scenario and its sign is "reduction".
        # Reporters read a signed percentage as "did the weather make it better",
        # so the two means and a plainly-labelled change travel with it.
        unpriced = statistics.fmean(row["dose"] for row in counterfactual)
        priced = statistics.fmean(row["dose"] for row in rows["gen2"])
        paired["mean_dose_unpriced"] = round(unpriced, 3)
        paired["mean_dose_priced"] = round(priced, 3)
        paired["dose_change_pct"] = round(100.0 * (priced - unpriced) / max(unpriced, 1e-9), 2)
    return {
        "layer": True,
        "profile": book.get("profile"),
        "profile_source": book.get("profile_source"),
        "panel": panel,
        "counterfactual": paired,
        "advisory_counts": book.get("advisory_counts") or {},
        "budget_permille": book.get("budget_permille"),
    }


def summarise_comparison(
    result: Dict[str, object], thresholds: Optional[Thresholds] = None
) -> Dict[str, object]:
    from .gate import COMPARATORS as OPS

    thresholds = thresholds or Thresholds()
    rows: Dict[str, List[Dict[str, float]]] = result["rows"]  # type: ignore[assignment]
    train, test = holdout_split(int(result["scenarios"]))  # type: ignore[arg-type]

    def effect(before_name: str, after_name: str, indices: Optional[Sequence[int]] = None) -> Dict[str, object]:
        indices = list(range(len(rows[before_name]))) if indices is None else list(indices)
        return _effect(
            [rows[before_name][i] for i in indices],
            [rows[after_name][i] for i in indices],
        )

    effects = {
        "gen1_vs_baseline": effect("baseline", "gen1"),
        "gen2_vs_baseline": effect("baseline", "gen2"),
        "gen2_vs_gen1": effect("gen1", "gen2"),
    }
    holdout = {
        "train": effect("gen1", "gen2", train),
        "test": effect("gen1", "gen2", test),
        "train_fraction": 0.5,
    }
    primary = effects["gen2_vs_gen1"]
    ablation = {
        group: {
            "uca_mean": round(statistics.fmean(row["uca"] for row in series), 3),
            "delta_uca": round(
                statistics.fmean(row["uca"] for row in series)
                - statistics.fmean(row["uca"] for row in rows["gen2"]),
                3,
            ),
        }
        for group, series in (result.get("ablation") or {}).items()
    }

    facts = {
        "uca_ci_low_pp": primary["uca_reduction_pp_ci95"][0],
        "dose_ci_low_pct": primary["dose_reduction_pct_ci95"][0],
        "blocks_delta_mean": primary["blocks_delta"]["mean"],
        "min_served": min(row["served"] for row in rows["gen2"]),
        "compliance_pct_value": round(
            statistics.fmean(row["compliance_pct_value"] for row in rows["gen2"]), 4
        ),
        "p_permutation": primary["uca_delta"]["p_permutation"],
        "cliffs_delta": primary["cliffs_delta_uca"],
        "dose_unit": round(statistics.fmean(row["dose_unit"] for row in rows["gen2"]), 4),
        "routed_qty": round(statistics.fmean(row["routed_qty"] for row in rows["gen2"]), 4),
    }
    # Limits that come from the run itself, not from the configuration file: a
    # non-inferiority test is against the comparator measured on the same seeds.
    run_limits = {
        "dose_unit_baseline": round(
            statistics.fmean(row["dose_unit"] for row in rows["baseline"]), 4
        ),
        "routed_qty_gen1": round(
            statistics.fmean(row["routed_qty"] for row in rows["gen1"]), 4
        ),
    }
    checks = []
    for name, fact, op, limit_key, hard in CRITERIA:
        limit = CONSTANT_LIMITS.get(
            limit_key, run_limits.get(limit_key, getattr(thresholds, limit_key, None))
        )
        passed = OPS[op](facts[fact], limit)
        checks.append(
            {
                "criterion": name,
                "fact": fact,
                "value": facts[fact],
                "operator": op,
                "limit": limit,
                "passed": bool(passed),
                "hard": hard,
            }
        )
    failed_hard = [check["criterion"] for check in checks if check["hard"] and not check["passed"]]
    status = "SEPARATES" if not failed_hard else "NO_SEPARATION"
    return {
        "scenarios": result["scenarios"],
        "seed": result["seed"],
        "intensity": result["intensity"],
        "elapsed_s": result["elapsed_s"],
        "first_hash": result["first_hash"],
        "means": {name: _means(rows[name]) for name in COMPARATORS},
        "effects": effects,
        "holdout": holdout,
        "ablation": ablation,
        "weather": _weather_summary(result, rows),
        "facts": facts,
        "checks": checks,
        "decision": {"status": status, "failed": failed_hard},
    }
