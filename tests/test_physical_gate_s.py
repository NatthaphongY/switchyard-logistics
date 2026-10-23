"""Directed tests for the four physical gate codes and the remedy hooks.

These are the cases the random corpus does not reach: a saturated station, a
dose over budget, a route below the availability floor, deliberate deferral, and
the three hooks that turn a finding off only when the plan actually paid for the
remedy. Without them the rules would be code that no scenario proves.
"""

from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from switchyard.gate import evaluate  # noqa: E402
from switchyard.model import (  # noqa: E402
    Consignment,
    Lane,
    LegPlan,
    Network,
    Node,
    Plan,
    Thresholds,
)


def _node(nid: str, capacity: float = 100.0, classes=("ambient", "chilled")) -> Node:
    return Node(
        id=nid,
        region="R0",
        classes=classes,
        dwell_p95_min=60,
        capacity_per_hour=capacity,
        assessed=True,
    )


def _lane(lid: str, src: str, dst: str, mode: str = "road", travel: int = 60, **kwargs) -> Lane:
    return Lane(
        id=lid,
        src=src,
        dst=dst,
        mode=mode,
        travel_min=travel,
        capacity_per_hour=kwargs.pop("capacity_per_hour", 100.0),
        cost_per_unit=kwargs.pop("cost_per_unit", 1.0),
        **kwargs,
    )


def _consignment(**kwargs) -> Consignment:
    base = dict(
        id="C00",
        origin="N00",
        dest="N01",
        qty=4.0,
        temp_class="chilled",
        ready_min=0,
        due_min=600,
        excursion_allowance_min=0,
        heat_gain_permille=1000,
        quality_budget_min=210,
    )
    base.update(kwargs)
    return Consignment(**base)


def _plan(legs, **kwargs) -> Plan:
    return Plan(
        legs=tuple(legs),
        pre_cool_verified=kwargs.pop("pre_cool_verified", {"C00": True}),
        **kwargs,
    )


def _codes(release) -> set:
    return {finding.code for finding in release.findings}


def test_queue_rule_fires_when_a_station_is_saturated():
    network = Network(
        name="queue",
        horizon_min=1440,
        nodes={"N00": _node("N00", capacity=0.5), "N01": _node("N01", capacity=100.0)},
        lanes=(_lane("L000", "N00", "N01"),),
        consignments=(_consignment(qty=40.0),),
    )
    plan = _plan([LegPlan(consignment="C00", lane="L000", depart_min=0, party="p")])
    assert "GATE-QUEUE-001" in _codes(evaluate(network, plan, {"notice_min": 60}))


def test_queue_rule_stays_silent_below_the_ceiling():
    network = Network(
        name="queue-ok",
        horizon_min=1440,
        nodes={"N00": _node("N00"), "N01": _node("N01")},
        lanes=(_lane("L000", "N00", "N01"),),
        consignments=(_consignment(),),
    )
    plan = _plan([LegPlan(consignment="C00", lane="L000", depart_min=0, party="p")])
    assert "GATE-QUEUE-001" not in _codes(evaluate(network, plan, {"notice_min": 60}))


def test_thermal_dose_rule_fires_over_budget_and_protection_clears_it():
    network = Network(
        name="therm",
        horizon_min=1440,
        nodes={"N00": _node("N00"), "N01": _node("N01")},
        lanes=(_lane("L000", "N00", "N01", travel=240, controlled=False),),
        consignments=(_consignment(quality_budget_min=120, heat_gain_permille=1300),),
    )
    thresholds = Thresholds()
    plain = _plan([LegPlan(consignment="C00", lane="L000", depart_min=0, party="p")])
    assert "GATE-THERM-006" in _codes(evaluate(network, plain, {"notice_min": 60}, thresholds))
    protected = replace(plain, thermal_protection=("C00",))
    assert "GATE-THERM-006" not in _codes(
        evaluate(network, protected, {"notice_min": 60}, thresholds)
    )


def test_reliability_rule_fires_below_the_floor_and_backup_clears_it():
    network = Network(
        name="reliab",
        horizon_min=1440,
        nodes={"N00": _node("N00"), "N01": _node("N01")},
        lanes=(_lane("L000", "N00", "N01", mode="air"),),
        consignments=(_consignment(),),
    )
    strict = replace(Thresholds(), availability_floor_permille=990)
    plan = _plan([LegPlan(consignment="C00", lane="L000", depart_min=0, party="p")])
    assert "GATE-RELIAB-001" in _codes(evaluate(network, plan, {"notice_min": 60}, strict))
    covered = replace(plan, backup_modes={"C00": "road"})
    assert "GATE-RELIAB-001" not in _codes(
        evaluate(network, covered, {"notice_min": 60}, strict)
    )


def test_service_floor_fires_only_on_deliberate_deferral():
    network = Network(
        name="service",
        horizon_min=1440,
        nodes={"N00": _node("N00"), "N01": _node("N01")},
        lanes=(_lane("L000", "N00", "N01"),),
        consignments=(_consignment(id="C00", qty=8.0), _consignment(id="C01", qty=2.0)),
    )
    shipped = Plan(
        legs=(LegPlan(consignment="C00", lane="L000", depart_min=0, party="p"),),
        pre_cool_verified={"C00": True},
    )
    assert "GATE-SERVICE-001" not in _codes(evaluate(network, shipped, {"notice_min": 60}))
    deferred = replace(shipped, deferred=("C01",))
    assert "GATE-SERVICE-001" in _codes(evaluate(network, deferred, {"notice_min": 60}))


def test_forward_stock_covers_a_flow_shortfall_only_when_committed():
    network = Network(
        name="flow",
        horizon_min=1440,
        nodes={"N00": _node("N00"), "N01": _node("N01")},
        lanes=(_lane("L000", "N00", "N01", capacity_per_hour=1.0),),
        consignments=(_consignment(qty=20.0, prepositioned_qty=15.0),),
    )
    plan = _plan([LegPlan(consignment="C00", lane="L000", depart_min=0, party="p")])
    assert "GATE-FLOW-001" in _codes(evaluate(network, plan, {"notice_min": 60}))
    committed = replace(plan, prepositioned={"C00": 15.0})
    assert "GATE-FLOW-001" not in _codes(evaluate(network, committed, {"notice_min": 60}))


def test_escrow_clears_the_counterparty_finding():
    network = Network(
        name="party",
        horizon_min=1440,
        nodes={"N00": _node("N00"), "N01": _node("N01")},
        lanes=(_lane("L000", "N00", "N01"),),
        consignments=(_consignment(),),
    )
    plan = _plan(
        [LegPlan(consignment="C00", lane="L000", depart_min=0, party="p")],
        counterparty_verified=False,
    )
    assert "GATE-PARTY-001" in _codes(evaluate(network, plan, {"notice_min": 60}))
    escrowed = replace(plan, escrowed=("C00",))
    assert "GATE-PARTY-001" not in _codes(evaluate(network, escrowed, {"notice_min": 60}))


def test_backup_mode_clears_the_single_mode_finding():
    network = Network(
        name="mode",
        horizon_min=1440,
        nodes={"N00": _node("N00"), "N01": _node("N01")},
        lanes=(_lane("L000", "N00", "N01", mode="road", blocked_until_min=240),),
        consignments=(_consignment(),),
    )
    plan = _plan([LegPlan(consignment="C00", lane="L000", depart_min=0, party="p")])
    assert "GATE-MODE-001" in _codes(evaluate(network, plan, {"notice_min": 60}))
    covered = replace(plan, backup_modes={"C00": "rail"})
    assert "GATE-MODE-001" not in _codes(evaluate(network, covered, {"notice_min": 60}))
