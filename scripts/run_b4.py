"""Gate B4 measurement, generation two.

Usage (from the worktree root):
    py -3.13 -X utf8 research/scripts/run_b4.py --scenarios 300 --ablation
    py -3.13 -X utf8 research/scripts/run_b4.py --scenarios 60 --seed 7 --json-only

Writes research/evidence/B4_MEASUREMENT_V2.json and .md. No network access, no
credentials, no graphics processor.
"""

from __future__ import annotations

import argparse
import json
import platform
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bhr_rs.compare import run_comparison, summarise_comparison  # noqa: E402
from bhr_rs.model import load_thresholds  # noqa: E402


def thresholds():
    payload = json.loads((ROOT / "config" / "thresholds.json").read_text(encoding="utf-8"))
    payload.pop("_comment", None)
    payload.pop("version", None)
    return load_thresholds(payload)


def _table(summary: dict) -> str:
    rows = [
        "| Metric | Current practice | Generation one | Generation two |",
        "|---|---|---|---|",
    ]
    labels = (
        ("uca", "Unsafe control actions per scenario"),
        ("blocks", "Blocking findings per scenario"),
        ("excursion", "Excursion minutes per scenario"),
        ("dose_unit", "Thermal dose per delivered unit (permille)"),
        ("routed_qty", "Quantity actually routed"),
        ("compliance_pct_value", "Compliance spend, % of cargo value"),
    )
    for key, label in labels:
        rows.append(
            f"| {label} | {summary['means']['baseline'][key]} | "
            f"{summary['means']['gen1'][key]} | {summary['means']['gen2'][key]} |"
        )
    return "\n".join(rows)


def _effects(summary: dict) -> str:
    rows = [
        "| Comparison | UCA reduction (pp, 95 % CI) | p (permutation) | Cliff's delta |",
        "|---|---|---|---|",
    ]
    for name, effect in summary["effects"].items():
        low, high = effect["uca_reduction_pp_ci95"]
        rows.append(
            f"| {name} | {effect['uca_reduction_pp']} ({low} to {high}) | "
            f"{effect['uca_delta']['p_permutation']} | {effect['cliffs_delta_uca']} |"
        )
    return "\n".join(rows)


def _checks(summary: dict) -> str:
    rows = ["| Criterion | Value | Operator | Limit | Passed |", "|---|---|---|---|---|"]
    for check in summary["checks"]:
        rows.append(
            f"| {check['criterion']} | {check['value']} | {check['operator']} | "
            f"{check['limit']} | {'yes' if check['passed'] else 'no'} |"
        )
    return "\n".join(rows)


def _ablation(summary: dict) -> str:
    if not summary["ablation"]:
        return "_Ablation not requested._"
    rows = ["| Remedy disabled | Mean UCA | Change versus full reference |", "|---|---|---|"]
    for group, row in sorted(summary["ablation"].items(), key=lambda item: -item[1]["delta_uca"]):
        rows.append(f"| {group} | {row['uca_mean']} | +{row['delta_uca']} |")
    return "\n".join(rows)


def _provenance(source: dict) -> str:
    """State where the region table came from, or that it is invented.

    A number without its provenance is a claim. This keeps the citation in the
    artefact itself, which is the only place a reader of the paper will look.
    """
    kind = source.get("kind", "unknown")
    if kind == "invented":
        return (
            "Profile provenance: invented placeholder table, retained so the "
            "2026-10-23 evidence replays exactly. Not a measurement of any corridor."
        )
    sites = ", ".join(
        f"{key} {value['name']}"
        for key, value in sorted((source.get("sites") or {}).items())
    )
    return (
        f"Profile provenance: {source.get('product')} ({source.get('kind')}), month "
        f"{source.get('month')}, period {source.get('period')}, retrieved "
        f"{source.get('retrieved_utc')}. Sites: {sites}. Licence: "
        f"{source.get('licence')}. Attribution: {source.get('attribution')}."
    )


def _weather(summary: dict) -> str:
    block = summary.get("weather") or {}
    if not block.get("layer"):
        return "_Weather layer not requested (`--weather`)._\n"
    rows = [
        "| Comparator | Mean p(any exceedance) | Share with any dose | Mean peak dose (permille) "
        "| Peak dose, % of budget | Mean expected dose (permille) | Mean value at risk (currency) |",
        "|---|---|---|---|---|---|---|",
    ]
    for name, cell in block["panel"].items():
        rows.append(
            f"| {name} | {cell['p_any_exceedance']} | {cell['share_dose_positive']} | "
            f"{cell['max_dose_permille']} | {cell['mean_dose_pct_budget']} | "
            f"{cell['expected_dose_permille']} | {cell['value_at_risk_usd']} |"
        )
    paired = block.get("counterfactual")
    if paired:
        low, high = paired["uca_reduction_pp_ci95"]
        rows += [
            "",
            "Paired effect of pricing weather into the heat gain, gen2 on the same "
            f"seeds: UCA {paired['uca_reduction_pp']} pp ({low} to {high}); mean total thermal dose "
            f"{paired['mean_dose_unpriced']} to {paired['mean_dose_priced']} permille "
            f"(aggregate means, {paired['dose_change_pct']} %, positive = the forecast raised "
            f"the dose); blocking findings delta {paired['blocks_delta']['mean']} (positive = "
            "weather raised them). The per-scenario paired change, averaged as a rate and "
            f"signed as a reduction, is {paired['dose_reduction_pct']} %. The two percentages "
            "differ because one weights a scenario by its size and the other weights every "
            "scenario equally; both say the forecast raised the dose.",
        ]
    advisories = block.get("advisory_counts") or {}
    rows += [
        "",
        f"Region profiles: `{block.get('profile')}`.",
        "",
        _provenance(block.get("profile_source") or {}),
        "",
        "Advisories raised by the weather layer (non-blocking by construction): "
        + (", ".join(f"{code} x{count}" for code, count in advisories.items()) or "none"),
        "",
        "Spread assumed for exceedance probability: sigma = 2.5 C forecast error, "
        "stated because the probability scales with it.",
        "",
        f"Budget the probability is measured against: {block.get('budget_permille')} permille of "
        "the thermal budget (the gate's own threshold). A probability of zero therefore reads as "
        "\"no shipment came near the budget\", not as \"exposure was not measured\" -- the share "
        "with any dose and the peak-dose-as-percentage columns are what make that distinction "
        "auditable.",
    ]
    return "\n".join(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Measure gate B4, generation two")
    parser.add_argument("--scenarios", type=int, default=300)
    parser.add_argument("--seed", type=int, default=20261023)
    parser.add_argument("--intensity", type=float, default=1.0)
    parser.add_argument("--ablation", action="store_true")
    parser.add_argument("--weather", action="store_true", help="Price ambient conditions into thermal risk")
    parser.add_argument(
        "--weather-profile",
        default=None,
        choices=("measured", "synthetic"),
        help="Region table: measured is the open reanalysis climatology (default), "
        "synthetic replays the earlier invented table so older numbers reproduce.",
    )
    parser.add_argument("--json-only", action="store_true")
    parser.add_argument(
        "--tag",
        default="",
        help="Suffix for the evidence files (e.g. WX writes B4_MEASUREMENT_V2_WX). "
        "Default writes B4_MEASUREMENT_V2, so the weather run does not overwrite the "
        "baseline the documents quote.",
    )
    args = parser.parse_args()

    result = run_comparison(
        scenarios=args.scenarios,
        seed=args.seed,
        intensity=args.intensity,
        thresholds=thresholds(),
        ablation=args.ablation,
        weather_layer=args.weather,
        weather_profile=args.weather_profile,
    )
    summary = summarise_comparison(result, thresholds())

    test = summary["holdout"]["test"]
    seed_line = (
        f"Seed {args.seed}, {args.scenarios} paired scenarios, intensity "
        f"{args.intensity}, elapsed {summary['elapsed_s']} s, Python "
        f"{platform.python_version()}."
    )
    layer_line = (
        "Ambient layer: on. Weather is priced into the consignment heat gain and "
        "the exceedance risk is read from the gate's own dose. Region table: "
        f"{summary['weather']['profile']}, with provenance in the section below."
        if args.weather
        else "Ambient layer: off. Heat gain is drawn directly by the scenario, so "
        "these numbers are the published baseline."
    )
    document = "\n".join(
        [
            "# Gate B4 measurement, generation two",
            "",
            seed_line,
            "",
            layer_line,
            "",
            _table(summary),
            "",
            "## Paired effects",
            "",
            _effects(summary),
            "",
            f"Holdout (second half of the seeds, untouched by any tuning): UCA "
            f"reduction {test['uca_reduction_pp_ci95'][0]} to "
            f"{test['uca_reduction_pp_ci95'][1]} pp, p = "
            f"{test['uca_delta']['p_permutation']}.",
            "",
            "## Pre-registered criteria",
            "",
            _checks(summary),
            "",
            f"Decision: **{summary['decision']['status']}**.",
            "",
            "## Ablation",
            "",
            _ablation(summary),
            "",
            "## Ambient conditions and risk",
            "",
            _weather(summary),
        ]
    )

    evidence = ROOT / "evidence"
    evidence.mkdir(exist_ok=True)
    stem = "B4_MEASUREMENT_V2" + (f"_{args.tag}" if args.tag else "")
    (evidence / f"{stem}.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8"
    )
    (evidence / f"{stem}.md").write_text(document + "\n", encoding="utf-8")
    if not args.json_only:
        print(document)
    print(f"\nwritten: research/evidence/{stem}.json and .md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
