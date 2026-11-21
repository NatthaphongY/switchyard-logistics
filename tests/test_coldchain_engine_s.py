"""Engine tests: catalyst gate codes, integer arithmetic, determinism, safe
composition, cascade reproduction number, and cross-language parity.
"""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from switchyard.cascade import catalyst_pressure, effective_reproduction, giant_component  # noqa: E402
from switchyard.evaluate import prepare  # noqa: E402
from switchyard.gate import evaluate  # noqa: E402
from switchyard.model import (  # noqa: E402
    Consignment,
    Lane,
    LegPlan,
    Network,
    Node,
    Plan,
    load_thresholds,
)
from switchyard.planners import plan_cost, plan_greedy, plan_priced  # noqa: E402
from switchyard.rng import StreamRandom  # noqa: E402
from switchyard.scenarios import scenario  # noqa: E402


def thresholds():
    thresholds_path = ROOT / "config" / "thresholds.json"
    try:
        payload = json.loads(
            thresholds_path.read_text(encoding="utf-8")
        )
    except (json.JSONDecodeError, ValueError) as exc:
        raise ValueError(f"Invalid JSON in {thresholds_path}: {exc}") from exc
    payload.pop("_comment", None)
    payload.pop("version", None)
    return load_thresholds(payload)


def network(cross_border: bool = False) -> Network:
    nodes = {
        "A": Node("A", "R0", ("ambient", "chilled", "frozen"), 120, 40.0),
        "B": Node("B", "R1", ("ambient", "chilled", "frozen"), 120, 40.0),
    }
    lane = Lane(
        id="L1", src="A", dst="B", mode="rail", travel_min=60,
        capacity_per_hour=20.0, cost_per_unit=1.0,
        monitored=True, controlled=True, blocked_until_min=0, cross_border=cross_border,
    )
    consignment = Consignment(
        id="C1", origin="A", dest="B", qty=5.0, temp_class="chilled",
        ready_min=0, due_min=600, excursion_allowance_min=0,
    )
    return Network("unit", 1440, nodes, (lane,), (consignment,))


def plan(**overrides) -> Plan:
    leg = LegPlan(consignment="C1", lane="L1", depart_min=10, party="carrier:rail",
                  door_confirmed=True)
    values = dict(
        legs=(leg,),
        pre_cool_verified={"C1": True},
        excursion_estimate_min={"C1": 0},
        capacity_verified=True,
        documents_verified=True,
        counterparty_verified=True,
        border_permits_held=True,
    )
    values.update(overrides)
    return Plan(**values)


def codes(release) -> set:
    return {finding.code for finding in release.findings}


def test_clean_plan_passes():
    assert evaluate(network(), plan()).verdict == "PASS"


def test_legal_code_fires_only_without_permits():
    blocked = evaluate(network(cross_border=True), plan(border_permits_held=False))
    assert "GATE-LEGAL-001" in codes(blocked)
    assert blocked.verdict == "BLOCKED"
    allowed = evaluate(network(cross_border=True), plan(border_permits_held=True))
    assert "GATE-LEGAL-001" not in codes(allowed)


def test_labour_code_fires_when_station_has_no_throughput():
    base = network()
    base.nodes["B"] = replace(base.nodes["B"], capacity_per_hour=0.0)
    assert "GATE-NODE-002" in codes(evaluate(base, plan()))


def test_counterparty_cyber_and_data_codes_fire():
    assert "GATE-PARTY-001" in codes(evaluate(network(), plan(counterparty_verified=False)))
    assert "GATE-HANDOFF-003" in codes(evaluate(network(), plan(documents_verified=False)))
    assert "GATE-DATA-002" in codes(evaluate(network(), plan(capacity_verified=False)))


def test_catalyst_pressure_is_bounded_and_ordered():
    calm = {"catalysts": {
        "geoeconomic": {"export_control": False, "tariff_shock_pct": 0.0},
        "labour": {"action": False, "vulnerability_index": 0.1},
        "financial": {"default": False, "solvency_score": 1.0},
        "cyber": {"intrusion": False, "digital_dependency": 0.2},
    }}
    stressed = {"catalysts": {
        "geoeconomic": {"export_control": True, "tariff_shock_pct": 0.35},
        "labour": {"action": True, "vulnerability_index": 0.9},
        "financial": {"default": True, "solvency_score": 0.15},
        "cyber": {"intrusion": True, "digital_dependency": 0.95},
    }}
    assert 0.0 <= catalyst_pressure(calm) < catalyst_pressure(stressed) <= 1.0
    grid, _ = scenario(7)
    calm_k = effective_reproduction(grid, 1.2) * (1.0 + catalyst_pressure(calm))
    hot_k = effective_reproduction(grid, 1.2) * (1.0 + catalyst_pressure(stressed))
    assert hot_k > calm_k
    assert 0.0 < giant_component(grid, "chilled") <= 1.0


def test_prepare_sets_flags_from_catalysts():
    event = {
        "information_state": "contradictory",
        "regulatory_gate": "customs",
        "catalysts": {
            "geoeconomic": {"export_control": True},
            "financial": {"solvency_score": 0.2},
            "cyber": {"intrusion": True},
        },
    }
    prepared = prepare(plan(), event)
    assert prepared.capacity_verified is False
    assert prepared.border_permits_held is False
    assert prepared.counterparty_verified is False
    assert prepared.documents_verified is False
    assert prepared.approvals_needed == 1


def test_composition_never_worse_than_baseline():
    limits = thresholds()
    for seed in (20261023, 20261024, 20261025, 20261026, 20261027):
        grid, event = scenario(seed)
        base = prepare(plan_greedy(grid, limits), event)
        base_release = evaluate(grid, base, event, limits)
        priced, _ = plan_priced(grid, limits, event=event)
        priced = prepare(priced, event)
        priced_release = evaluate(grid, priced, event, limits)
        base_key = (base_release.blocks, base_release.unsafe_control_actions,
                    base_release.excursion_total, plan_cost(grid, base))
        priced_key = (priced_release.blocks, priced_release.unsafe_control_actions,
                      priced_release.excursion_total, plan_cost(grid, priced))
        assert min(base_key, priced_key) <= base_key


def test_rng_regression_vector():
    stream = StreamRandom(1)
    assert [stream.next_u64() for _ in range(3)] == [
        5180492295206395165,
        12380297144915551517,
        13389498078930870103,
    ]


def test_same_seed_same_release_hash():
    limits = thresholds()
    grid, event = scenario(20261023)
    candidate = prepare(plan_greedy(grid, limits), event)
    assert evaluate(grid, candidate, event, limits).hash == evaluate(
        grid, candidate, event, limits
    ).hash


def test_rust_core_agrees_with_reference():
    binary = ROOT / "engine" / "target" / "release" / "switchyard-core.exe"
    instances = ROOT / "evidence" / "instances.txt"
    if not binary.exists() or not instances.exists():
        pytest.skip("Rust core or instances not built")
    completed = subprocess.run(
        [str(binary), "--instances", str(instances), "--threads", "2"],
        capture_output=True, text=True, check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "mismatches=0" in completed.stdout

