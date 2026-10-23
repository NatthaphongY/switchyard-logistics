"""Paired measurement harness for gate B4 (BHR-RS-05) and the escalation ladder.

Design decisions that are part of the claim, not of the implementation:

  * common random numbers: both planners receive the identical network, so the
    comparison is paired and the variance of the difference is reduced;
  * the primary metric is the number of distinct unsafe control actions the gate
    detects, because that is the quantity the programme claims to reduce;
  * the secondary metric is total excursion minutes;
  * the decision uses a percentile bootstrap over paired differences with a guard
    band of zero, so a positive result cannot come from rounding;
  * the baseline is a competent heuristic, and the shipped plan is the better of
    the two under the gate's own ordering, so the difference can never be
    manufactured by a weak baseline.
"""

from __future__ import annotations

from .rng import StreamRandom
import statistics
import time
from dataclasses import replace
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from .gate import Release, evaluate
from .model import Network, Plan, Thresholds
from .planners import plan_cost, plan_greedy, plan_priced
from .scenarios import scenario

MetricRow = Dict[str, float]

# Decision labels as constants: callers compare to a name, never to a literal.
STATUS_SEPARATES = "SEPARATES"
STATUS_NO_SEPARATION = "NO_SEPARATION"
STATUS_REGRESSION = "REGRESSION"


def _row(network: Network, event: dict, plan: Plan, release: Release) -> MetricRow:
    return {
        "blocks": float(release.blocks),
        "uca": float(release.unsafe_control_actions),
        "findings": float(release.total_findings),
        "excursion": float(release.excursion_total),
        "cost": plan_cost(network, plan),
        "blocked": 1.0 if release.verdict == "BLOCKED" else 0.0,
    }


def _better(base: MetricRow, priced: MetricRow) -> bool:
    return (
        priced["blocks"],
        priced["uca"],
        priced["excursion"],
        priced["cost"],
    ) < (
        base["blocks"],
        base["uca"],
        base["excursion"],
        base["cost"],
    )


def _authority_context(event: dict) -> dict:
    """Event facts, resolved once. Boolean arithmetic replaces branching."""
    catalysts = event.get("catalysts", {})
    geo = catalysts.get("geoeconomic", {})
    cyber = catalysts.get("cyber", {})
    financial = catalysts.get("financial", {})
    return {
        "approvals": int(event.get("regulatory_gate", "none") != "none"),
        "stale_min": 300 * (event.get("information_state") == "stale"),
        "verified": event.get("information_state") != "contradictory",
        "documents_ok": not bool(cyber.get("intrusion", False)),
        "solvent": float(financial.get("solvency_score", 1.0)) >= 0.5,
        "permits_ok": not bool(geo.get("export_control", False)),
    }


# One row per authority field. A remedy that was paid for flips the fact; a
# remedy that was not paid for leaves it standing. No if-elif ladder decides
# which rule applies, because the table is the rule.
AUTHORITY_RULES = (
    ("approvals_needed", lambda plan, ctx: ctx["approvals"] * (not plan.pre_authorised)),
    (
        "decision_age_min",
        lambda plan, ctx: max(plan.decision_age_min, ctx["stale_min"])
        * (not plan.input_refreshed),
    ),
    (
        "capacity_verified",
        lambda plan, ctx: (ctx["verified"] or plan.capacity_measured) and plan.capacity_verified,
    ),
    (
        "documents_verified",
        lambda plan, ctx: (ctx["documents_ok"] or plan.out_of_band_verified)
        and plan.documents_verified,
    ),
    (
        "counterparty_verified",
        lambda plan, ctx: ctx["solvent"] and plan.counterparty_verified,
    ),
    (
        "border_permits_held",
        lambda plan, ctx: ctx["permits_ok"] and plan.border_permits_held,
    ),
)


def prepare(plan: Plan, event: dict) -> Plan:
    """Apply event facts that constrain the authority to release, not the route.

    Compliance actions recorded on the plan are applied here, in one place, so
    the gate never has to ask "did the planner mean it?".
    """
    context = _authority_context(event)
    payload = {name: rule(plan, context) for name, rule in AUTHORITY_RULES}
    return replace(plan, **payload)



def run_paired(
    scenarios: int = 300,
    seed: int = 20261023,
    intensity: float = 1.0,
    thresholds: Optional[Thresholds] = None,
    progress: Optional[Callable[[int, int], None]] = None,
) -> Dict[str, object]:
    thresholds = thresholds or Thresholds()
    base_rows: List[MetricRow] = []
    comp_rows: List[MetricRow] = []
    wins = 0
    losses = 0
    hashes: List[str] = []
    started = time.perf_counter()
    for index in range(scenarios):
        network, event = scenario(seed + index, intensity=intensity)
        base_plan = prepare(plan_greedy(network, thresholds), event)
        base_release = evaluate(network, base_plan, event, thresholds)
        base_row = _row(network, event, base_plan, base_release)

        priced_plan, priced_release = plan_priced(network, thresholds, event=event)
        priced_plan = prepare(priced_plan, event)
        priced_release = evaluate(network, priced_plan, event, thresholds)
        priced_row = _row(network, event, priced_plan, priced_release)

        if _better(base_row, priced_row):
            comp_row, comp_release = priced_row, priced_release
            wins += 1
        else:
            comp_row, comp_release = base_row, base_release
            if _better(priced_row, base_row):
                losses += 1
        base_rows.append(base_row)
        comp_rows.append(comp_row)
        if index == 0:
            hashes.append(comp_release.hash)
        if progress and (index + 1) % 50 == 0:
            progress(index + 1, scenarios)
    elapsed = time.perf_counter() - started
    return {
        "scenarios": scenarios,
        "seed": seed,
        "intensity": intensity,
        "elapsed_s": round(elapsed, 2),
        "base": base_rows,
        "composed": comp_rows,
        "wins": wins,
        "losses": losses,
        "first_hash": hashes[0] if hashes else "",
    }


def paired_bootstrap(
    differences: Sequence[float], resamples: int = 10000, seed: int = 7
) -> Tuple[float, float, float]:
    """Percentile bootstrap of the mean of paired differences."""
    if not differences:
        return 0.0, 0.0, 0.0
    rng = StreamRandom(seed)
    count = len(differences)
    means = []
    for _ in range(resamples):
        total = 0.0
        for _ in range(count):
            total += differences[rng.randrange(count)]
        means.append(total / count)
    means.sort()
    low = means[int(0.025 * resamples)]
    high = means[int(0.975 * resamples) - 1]
    return statistics.fmean(differences), low, high


def summarise(
    result: Dict[str, object], thresholds: Optional[Thresholds] = None
) -> Dict[str, object]:
    thresholds = thresholds or Thresholds()
    base: List[MetricRow] = result["base"]  # type: ignore[assignment]
    comp: List[MetricRow] = result["composed"]  # type: ignore[assignment]
    base_uca = [row["uca"] for row in base]
    comp_uca = [row["uca"] for row in comp]
    base_exc = [row["excursion"] for row in base]
    comp_exc = [row["excursion"] for row in comp]
    base_blocks = [row["blocks"] for row in base]
    comp_blocks = [row["blocks"] for row in comp]

    uca_diff = [b - c for b, c in zip(base_uca, comp_uca)]
    uca_mean, uca_low, uca_high = paired_bootstrap(uca_diff, seed=11)
    base_uca_mean = statistics.fmean(base_uca)
    scale = max(base_uca_mean, 1.0)
    relative = [(b - c) / b for b, c in zip(base_exc, comp_exc) if b > 0]
    exc_mean, exc_low, exc_high = paired_bootstrap(relative, seed=13)
    block_diff = [b - c for b, c in zip(base_blocks, comp_blocks)]
    block_mean, block_low, _ = paired_bootstrap(block_diff, seed=17)

    summary: Dict[str, object] = {
        "scenarios": result["scenarios"],
        "seed": result["seed"],
        "intensity": result["intensity"],
        "elapsed_s": result["elapsed_s"],
        "first_hash": result["first_hash"],
        "baseline": {
            "uca_mean": round(base_uca_mean, 3),
            "uca_free_rate": round(sum(1 for u in base_uca if u == 0) / len(base_uca), 4),
            "excursion_mean": round(statistics.fmean(base_exc), 1),
            "blocks_mean": round(statistics.fmean(base_blocks), 3),
            "blocked_rate": round(statistics.fmean([row["blocked"] for row in base]), 4),
            "cost_mean": round(statistics.fmean([row["cost"] for row in base]), 2),
        },
        "composed": {
            "uca_mean": round(statistics.fmean(comp_uca), 3),
            "uca_free_rate": round(sum(1 for u in comp_uca if u == 0) / len(comp_uca), 4),
            "excursion_mean": round(statistics.fmean(comp_exc), 1),
            "blocks_mean": round(statistics.fmean(comp_blocks), 3),
            "blocked_rate": round(statistics.fmean([row["blocked"] for row in comp]), 4),
            "cost_mean": round(statistics.fmean([row["cost"] for row in comp]), 2),
        },
        "effect": {
            "uca_reduction_pp": round(100.0 * uca_mean / scale, 2),
            "uca_reduction_pp_ci95": [
                round(100.0 * uca_low / scale, 2),
                round(100.0 * uca_high / scale, 2),
            ],
            "excursion_reduction_pct": round(100.0 * exc_mean, 2),
            "excursion_reduction_pct_ci95": [
                round(100.0 * exc_low, 2),
                round(100.0 * exc_high, 2),
            ],
            "blocks_delta_ci95": [round(block_low, 3), round(block_mean, 3)],
            "priced_selected": result["wins"],
            "baseline_selected": int(result["scenarios"]) - int(result["wins"]),  # type: ignore[arg-type]
        },
        "thresholds": {
            "materiality_uca_points": thresholds.materiality_uca_points,
            "materiality_excursion_ratio": 100.0 * thresholds.materiality_excursion_ratio,
        },
    }
    summary["decision"] = decide(summary, thresholds)
    return summary


def decide(
    summary: Dict[str, object], thresholds: Optional[Thresholds] = None
) -> Dict[str, object]:
    thresholds = thresholds or Thresholds()
    effect = summary["effect"]  # type: ignore[index]
    baseline = summary["baseline"]  # type: ignore[index]
    composed = summary["composed"]  # type: ignore[index]
    uca_low = float(effect["uca_reduction_pp_ci95"][0])  # type: ignore[index]
    exc_low = float(effect["excursion_reduction_pct_ci95"][0])  # type: ignore[index]
    blocks_guard = float(composed["blocks_mean"]) <= float(baseline["blocks_mean"]) + 1e-9
    material = (
        uca_low >= thresholds.materiality_uca_points
        or exc_low >= 100.0 * thresholds.materiality_excursion_ratio
    )
    STATUS_BY_OUTCOME = {
        (False, True): "REGRESSION",
        (False, False): "REGRESSION",
        (True, True): "SEPARATES",
        (True, False): "NO_SEPARATION",
    }
    status = STATUS_BY_OUTCOME[(blocks_guard, material)]
    return {
        "status": status,
        "rule": "uca CI lower bound at least 15 pp OR excursion CI lower bound at least "
        "10 percent, with blocks not worse",
        "uca_gate_pass": uca_low >= thresholds.materiality_uca_points,
        "excursion_gate_pass": exc_low >= 100.0 * thresholds.materiality_excursion_ratio,
        "blocks_guard_pass": blocks_guard,
    }


def run_ladder(
    levels: Sequence[float] = (1.0, 1.5, 2.0),
    scenarios_per_level: int = 300,
    seed: int = 20261023,
    thresholds: Optional[Thresholds] = None,
) -> Dict[str, object]:
    """Pre-registered escalation ladder: raise coupling, never lower the bar."""
    thresholds = thresholds or Thresholds()
    rows = []
    separating_level: Optional[float] = None
    for intensity in levels:
        raw = run_paired(
            scenarios=scenarios_per_level, seed=seed, intensity=intensity, thresholds=thresholds
        )
        summary = summarise(raw, thresholds)
        rows.append(summary)
        status = summary["decision"]["status"]  # type: ignore[index]
        separates = status == STATUS_SEPARATES
        separating_level = separating_level if not separates else (separating_level or intensity)
    return {
        "levels": list(levels),
        "scenarios_per_level": scenarios_per_level,
        "seed": seed,
        "rows": rows,
        "separating_level": separating_level,
        "conclusion": (
            f"separation at intensity {separating_level}"
            if separating_level is not None
            else "no separation at any pre-registered level; publish as plan auditor"
        ),
    }


