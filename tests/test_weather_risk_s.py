"""Weather layer and thermal risk: determinism, parity and honest limits.

These tests pin the four claims the paper makes about SW-11:

* the weather report is a pure function of the scenario seed (integer only), so
  the Rust replay sees the same numbers;
* ambient conditions enter through `heat_gain_permille` and nothing else, which
  is why pricing weather needs no change to the evaluator or the planners;
* advisories are advice -- they never add a blocking finding to a release;
* the exceedance probability is a monotone reading of the gate's measured dose,
  zero when nothing was exposed, and above one half when the dose is already over
  budget (an honest reading of a failing shipment, not a clamp).
"""

from __future__ import annotations

import dataclasses
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from switchyard import risk, vector, weather  # noqa: E402
from switchyard.compare import (  # noqa: E402
    COMPARATORS,
    _plan_for,
    run_comparison,
    summarise_comparison,
)
from switchyard.evaluate import prepare  # noqa: E402
from switchyard.gate import evaluate  # noqa: E402
from switchyard.model import Thresholds  # noqa: E402
from switchyard.scenarios import scenario  # noqa: E402

SEEDS = range(1, 13)


def test_weather_report_is_a_pure_function_of_the_seed():
    for seed in SEEDS:
        _, event = scenario(seed)
        first = weather.assess(event, seed=seed)
        second = weather.assess(event, seed=seed)
        assert first == second
        for region in first.regions:
            assert isinstance(region.peak_c_tenths, int)
            assert isinstance(region.storm_permille, int)


def test_different_seeds_give_different_reports():
    reports = set()
    for seed in SEEDS:
        _, event = scenario(seed)
        report = weather.assess(event, seed=seed)
        reports.add(
            (
                report.severity_c_tenths,
                tuple(sorted(report.multiplier_permille.items())),
                tuple(sorted(report.degrees_above_band.items())),
            )
        )
    assert len(reports) > 1


def test_weather_is_priced_only_through_heat_gain():
    ceiling = weather.config()["heat_ceiling_permille"]
    for seed in SEEDS[:6]:
        network, event = scenario(seed)
        report = weather.assess(event, seed=seed)
        priced = weather.apply(network, report)
        assert priced.horizon_min == network.horizon_min
        assert priced.lanes == network.lanes
        assert priced.nodes == network.nodes
        for before, after in zip(network.consignments, priced.consignments):
            assert isinstance(after.heat_gain_permille, int)
            assert after.heat_gain_permille >= before.heat_gain_permille
            assert after.heat_gain_permille <= ceiling
            assert (
                dataclasses.replace(before, heat_gain_permille=after.heat_gain_permille)
                == after
            )


def test_advisories_never_block_a_release():
    thresholds = Thresholds()
    for seed in SEEDS:
        network, event = scenario(seed)
        report = weather.assess(event, seed=seed)
        priced = weather.apply(network, report)
        for name in COMPARATORS:
            plan = prepare(_plan_for(name, priced, thresholds, event), event)
            for finding in weather.findings(priced, plan, report):
                assert finding["severity"] == "warn"
                assert finding["code"].startswith("WX-ADV-")
            release = evaluate(priced, plan, event, thresholds)
            assert not [f for f in release.findings if f.code.startswith("WX-ADV-")]


def test_zero_dose_carries_zero_exceedance_risk():
    network, event = scenario(3)
    report = weather.assess(event, seed=3)
    consignment = network.consignments[0]
    row = risk.thermal_exceedance(consignment, 0, report)
    assert row["p_exceedance"] == 0.0
    assert row["value_at_risk_usd"] == 0.0


def test_exceedance_rises_with_dose_and_is_one_half_at_the_budget():
    network, event = scenario(5)
    report = weather.assess(event, seed=5)
    consignment = network.consignments[0]
    doses = [0, 1, 10, 100, 500, 1000, 1500, 2000]
    probabilities = [
        risk.thermal_exceedance(consignment, dose, report)["p_exceedance"] for dose in doses
    ]
    assert probabilities == sorted(probabilities)
    assert risk.thermal_exceedance(consignment, 1000, report)["p_exceedance"] == 0.5
    assert risk.thermal_exceedance(consignment, 2000, report)["p_exceedance"] > 0.5


def test_spread_is_reported_so_the_probability_can_be_reproduced():
    network, event = scenario(9)
    report = weather.assess(event, seed=9)
    consignment = network.consignments[0]
    row = risk.thermal_exceedance(consignment, 1200, report, sigma_c=2.5)
    assert row["relative_sigma"] == risk.relative_sigma(consignment.temp_class, 2.5)
    assert round(row["relative_sigma"], 4) == row["relative_sigma"]
    wider = risk.thermal_exceedance(consignment, 1200, report, sigma_c=5.0)
    assert wider["relative_sigma"] > row["relative_sigma"]


def test_zero_spread_is_deterministic_not_a_division_by_zero():
    """The guard regime must answer, not raise: a paper cannot report NaN."""
    network, event = scenario(11)
    report = weather.assess(event, seed=11)
    consignment = network.consignments[0]
    under = risk.thermal_exceedance(consignment, 500, report, sigma_c=0.0)
    at = risk.thermal_exceedance(consignment, 1000, report, sigma_c=0.0)
    over = risk.thermal_exceedance(consignment, 1500, report, sigma_c=0.0)
    assert (under["p_exceedance"], at["p_exceedance"], over["p_exceedance"]) == (0.0, 0.0, 1.0)
    assert under["relative_sigma"] == 0.0


def test_portfolio_uses_the_gates_own_dose():
    network, event = scenario(4)
    report = weather.assess(event, seed=4)
    priced = weather.apply(network, report)
    thresholds = Thresholds()
    plan = prepare(_plan_for("gen2", priced, thresholds, event), event)
    release = evaluate(priced, plan, event, thresholds)
    book = risk.portfolio(priced, plan, release, report)
    assert 0.0 <= book["p_any_exceedance"] <= 1.0
    assert book["max_dose_permille"] == max(
        (row["dose_permille"] for row in book["rows"]), default=0
    )
    assert book["max_dose_permille"] == max(release.thermal_dose.values(), default=0)
    assert book["value_at_risk_usd"] == round(
        sum(row["value_at_risk_usd"] for row in book["rows"]), 2
    )
    assert len(book["rows"]) == len(priced.consignments)
    assert all(isinstance(row["dose_permille"], int) for row in book["rows"])


def test_vector_is_thirty_six_integers_and_names_them():
    network, event = scenario(11)
    report = weather.assess(event, seed=11)
    row = vector.vector(network, event, report)
    assert len(row) == 36
    assert vector.manifest()["dimension_count"] == 36
    assert all(isinstance(value, int) for value in row)
    named = vector.as_dict(row)
    assert tuple(named) == vector.COLUMNS
    assert named["time.horizon_min"] == network.horizon_min
    assert named["network.lane_count"] == len(network.lanes)


def test_vector_leaves_risk_columns_at_zero_without_a_gate_run():
    network, event = scenario(11)
    named = vector.as_dict(vector.vector(network, event, weather.assess(event, seed=11)))
    assert named["risk.p_exceedance"] == 0
    assert named["risk.expected_dose"] == 0
    assert named["risk.value_at_risk"] == 0


def test_vector_reads_risk_columns_from_the_same_dose_the_gate_reported():
    """The wired path: plan and release given, the three risk columns are the book.

    Seed 10 is used deliberately: it is an exposed scenario (the tail the panel
    averages over), so the columns carry non-zero readings and the test can tell
    a priced network from an un-priced one.
    """
    network, event = scenario(10)
    report = weather.assess(event, seed=10)
    priced = weather.apply(network, report)
    thresholds = Thresholds()
    plan = prepare(_plan_for("gen2", priced, thresholds, event), event)
    release = evaluate(priced, plan, event, thresholds)
    named = vector.as_dict(vector.vector(priced, event, report, release=release, plan=plan))
    book = risk.portfolio(
        priced, plan, release, report, threshold_permille=thresholds.thermal_budget_permille
    )
    assert named["risk.expected_dose"] == int(book["expected_dose_permille"])
    assert named["risk.p_exceedance"] == int(round(book["p_any_exceedance"] * 1000))
    assert named["risk.value_at_risk"] == int(round(book["value_at_risk_usd"]))
    assert named["risk.expected_dose"] > 0
    # An unpriced network and a priced one must not produce the same risk row:
    # otherwise the layer is present but silent, which reads as safety.
    plain_plan = prepare(_plan_for("gen2", network, thresholds, event), event)
    plain_release = evaluate(network, plain_plan, event, thresholds)
    unpriced = vector.as_dict(
        vector.vector(
            network,
            event,
            weather.assess(event, seed=10),
            release=plain_release,
            plan=plain_plan,
        )
    )
    assert (
        unpriced["risk.expected_dose"],
        unpriced["risk.p_exceedance"],
        unpriced["risk.value_at_risk"],
    ) != (
        named["risk.expected_dose"],
        named["risk.p_exceedance"],
        named["risk.value_at_risk"],
    )


def test_weather_run_is_reproducible_apart_from_the_clock():
    """Two runs of the same seed give the same evidence, wall clock aside.

    The published artefact carries `elapsed_s`, which is the only field allowed
    to differ; everything a reader might cite has to be identical.
    """
    first = run_comparison(scenarios=5, seed=99, weather_layer=True)
    second = run_comparison(scenarios=5, seed=99, weather_layer=True)
    assert first.pop("elapsed_s") >= 0.0
    assert second.pop("elapsed_s") >= 0.0
    assert first == second


def test_comparison_without_the_layer_keeps_the_old_table():
    result = run_comparison(scenarios=2, seed=4242)
    assert result["weather"]["layer"] is False
    assert all("p_exceedance" not in row for row in result["rows"]["gen2"])
    assert summarise_comparison(result)["weather"] == {"layer": False}


def test_comparison_with_the_layer_reports_a_measurable_panel():
    result = run_comparison(scenarios=3, seed=4242, weather_layer=True)
    assert result["weather"]["layer"] is True
    assert len(result["weather"]["counterfactual"]) == 3
    panel = summarise_comparison(result)["weather"]["panel"]
    assert tuple(panel) == COMPARATORS
    for cell in panel.values():
        assert 0.0 <= cell["p_any_exceedance"] <= 1.0
        assert 0.0 <= cell["share_dose_positive"] <= 1.0
        assert cell["value_at_risk_usd"] >= 0.0
    paired = summarise_comparison(result)["weather"]["counterfactual"]
    assert paired is not None
    assert set(paired) >= {
        "uca_reduction_pp",
        "dose_reduction_pct",
        "blocks_delta",
        "mean_dose_unpriced",
        "mean_dose_priced",
        "dose_change_pct",
    }
    # Sign convention is explicit so a reader cannot invert the claim.
    assert paired["dose_change_pct"] == round(
        100.0
        * (paired["mean_dose_priced"] - paired["mean_dose_unpriced"])
        / max(paired["mean_dose_unpriced"], 1e-9),
        2,
    )
    assert summary_budget_matches_budget(summarise_comparison(result))


def summary_budget_matches_budget(summary: dict) -> bool:
    return summary["weather"]["budget_permille"] == Thresholds().thermal_budget_permille

