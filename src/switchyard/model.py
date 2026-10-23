"""Data model for the event-agnostic cold-chain compliance gate.

Documents: SW-02 (architecture), SW-06 (normative specification).
All structures are immutable and hashable through a canonical JSON encoding, so a
plan and its verdict can be replayed byte for byte (SW-06 section 9).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, replace
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

AMBIENT = "ambient"
CHILLED = "chilled"
FROZEN = "frozen"


@dataclass(frozen=True)
class Node:
    id: str
    region: str
    classes: Tuple[str, ...]
    dwell_p95_min: int
    capacity_per_hour: float
    assessed: bool = True


@dataclass(frozen=True)
class Lane:
    id: str
    src: str
    dst: str
    mode: str
    travel_min: int
    capacity_per_hour: float
    cost_per_unit: float
    monitored: bool = True
    controlled: bool = True
    blocked_until_min: int = 0
    cross_border: bool = False

    def usable(self, depart_min: int) -> bool:
        return depart_min >= self.blocked_until_min


@dataclass(frozen=True)
class Consignment:
    id: str
    origin: str
    dest: str
    qty: float
    temp_class: str
    ready_min: int
    due_min: int
    excursion_allowance_min: int = 0
    heat_gain_permille: int = 1000
    quality_budget_min: int = 210
    criticality: int = 1
    value_usd: float = 0.0
    prepositioned_qty: float = 0.0

    @property
    def needs_cold_chain(self) -> bool:
        return self.temp_class != AMBIENT


@dataclass(frozen=True)
class Network:
    name: str
    horizon_min: int
    nodes: Dict[str, Node]
    lanes: Tuple[Lane, ...]
    consignments: Tuple[Consignment, ...]

    def lane(self, lane_id: str) -> Lane:
        for candidate in self.lanes:
            if candidate.id == lane_id:
                return candidate
        raise KeyError(lane_id)

    def consignment(self, cid: str) -> Consignment:
        for candidate in self.consignments:
            if candidate.id == cid:
                return candidate
        raise KeyError(cid)

    def outgoing(self, node_id: str) -> List[Lane]:
        return [lane for lane in self.lanes if lane.src == node_id]


@dataclass(frozen=True)
class LegPlan:
    consignment: str
    lane: str
    depart_min: int
    party: Optional[str] = None
    door_confirmed: bool = True
    container: Optional[str] = None


@dataclass(frozen=True)
class Plan:
    legs: Tuple[LegPlan, ...] = ()
    decision_age_min: int = 0
    pre_cool_verified: Dict[str, bool] = field(default_factory=dict)
    excursion_disposition: Dict[str, bool] = field(default_factory=dict)
    excursion_estimate_min: Dict[str, int] = field(default_factory=dict)
    approvals_needed: int = 0
    capacity_verified: bool = True
    documents_verified: bool = True
    counterparty_verified: bool = True
    border_permits_held: bool = True
    cost_reduction_accepted: Tuple[str, ...] = ()
    strategy: str = "unspecified"
    # Compliance actions. Each one is a documented remedy in GATE-.../REMEDY, and
    # each one carries a price in config/physics.json so it is never free.
    pre_authorised: bool = False
    input_refreshed: bool = False
    capacity_measured: bool = False
    out_of_band_verified: bool = False
    escrowed: Tuple[str, ...] = ()
    backup_modes: Dict[str, str] = field(default_factory=dict)
    thermal_protection: Tuple[str, ...] = ()
    prepositioned: Dict[str, float] = field(default_factory=dict)
    deferred: Tuple[str, ...] = ()
    remedies: Tuple[str, ...] = ()

    def legs_of(self, consignment_id: str) -> List[LegPlan]:
        return sorted(
            (leg for leg in self.legs if leg.consignment == consignment_id),
            key=lambda leg: leg.depart_min,
        )


@dataclass(frozen=True)
class Thresholds:
    freshness_limit_min: int = 240
    handoff_max_min: int = 90
    materiality_uca_points: float = 15.0
    materiality_excursion_ratio: float = 0.10
    queue_ceiling_permille: int = 950
    availability_floor_permille: int = 900
    service_floor_permille: int = 950
    thermal_budget_permille: int = 1000
    dose_materiality_pct: float = 10.0
    cost_budget_pct_of_value: float = 0.5


def load_thresholds(payload: Optional[dict]) -> Thresholds:
    """Thresholds are data (README section 3, item 7). Unknown keys are rejected."""
    if not payload:
        return Thresholds()
    known = {f for f in Thresholds.__dataclass_fields__}  # type: ignore[attr-defined]
    unknown = set(payload) - known
    if unknown:
        raise ValueError(f"unknown threshold keys: {sorted(unknown)}")
    return Thresholds(**payload)


def canonical_json(payload: object) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def content_hash(payload: object) -> str:
    return hashlib.sha256(canonical_json(payload).encode("ascii")).hexdigest()[:32]


def network_to_dict(network: Network) -> dict:
    return {
        "name": network.name,
        "horizon_min": network.horizon_min,
        "nodes": {
            nid: {
                "region": node.region,
                "classes": list(node.classes),
                "dwell_p95_min": node.dwell_p95_min,
                "capacity_per_hour": node.capacity_per_hour,
                "assessed": node.assessed,
            }
            for nid, node in sorted(network.nodes.items())
        },
        "lanes": [
            {
                "id": lane.id,
                "src": lane.src,
                "dst": lane.dst,
                "mode": lane.mode,
                "travel_min": lane.travel_min,
                "capacity_per_hour": lane.capacity_per_hour,
                "cost_per_unit": lane.cost_per_unit,
                "monitored": lane.monitored,
                "controlled": lane.controlled,
                "blocked_until_min": lane.blocked_until_min,
            }
            for lane in network.lanes
        ],
        "consignments": [
            {
                "id": c.id,
                "origin": c.origin,
                "dest": c.dest,
                "qty": c.qty,
                "temp_class": c.temp_class,
                "ready_min": c.ready_min,
                "due_min": c.due_min,
                "excursion_allowance_min": c.excursion_allowance_min,
                "heat_gain_permille": c.heat_gain_permille,
                "quality_budget_min": c.quality_budget_min,
                "criticality": c.criticality,
                "value_usd": c.value_usd,
                "prepositioned_qty": c.prepositioned_qty,
            }
            for c in network.consignments
        ],
    }


def plan_to_dict(plan: Plan) -> dict:
    return {
        "strategy": plan.strategy,
        "decision_age_min": plan.decision_age_min,
        "approvals_needed": plan.approvals_needed,
        "capacity_verified": plan.capacity_verified,
        "documents_verified": plan.documents_verified,
        "counterparty_verified": plan.counterparty_verified,
        "border_permits_held": plan.border_permits_held,
        "pre_cool_verified": dict(sorted(plan.pre_cool_verified.items())),
        "excursion_disposition": dict(sorted(plan.excursion_disposition.items())),
        "excursion_estimate_min": dict(sorted(plan.excursion_estimate_min.items())),
        "cost_reduction_accepted": sorted(plan.cost_reduction_accepted),
        "pre_authorised": plan.pre_authorised,
        "input_refreshed": plan.input_refreshed,
        "capacity_measured": plan.capacity_measured,
        "out_of_band_verified": plan.out_of_band_verified,
        "escrowed": sorted(plan.escrowed),
        "backup_modes": dict(sorted(plan.backup_modes.items())),
        "thermal_protection": sorted(plan.thermal_protection),
        "prepositioned": dict(sorted(plan.prepositioned.items())),
        "deferred": sorted(plan.deferred),
        "remedies": sorted(plan.remedies),
        "legs": [
            {
                "consignment": leg.consignment,
                "lane": leg.lane,
                "depart_min": leg.depart_min,
                "party": leg.party,
                "door_confirmed": leg.door_confirmed,
                "container": leg.container,
            }
            for leg in sorted(plan.legs, key=lambda l: (l.consignment, l.depart_min, l.lane))
        ],
    }


def plan_hash(
    network: Network, plan: Plan, event_vector: Optional[dict], thresholds: Thresholds
) -> str:
    return content_hash(
        {
            "network": network_to_dict(network),
            "plan": plan_to_dict(plan),
            "event": event_vector or {},
            "thresholds": {
                f: getattr(thresholds, f)
                for f in Thresholds.__dataclass_fields__  # type: ignore[attr-defined]
            },
        }
    )


def with_lanes(network: Network, lanes: Sequence[Lane]) -> Network:
    return replace(network, lanes=tuple(lanes))


def with_consignments(network: Network, consignments: Sequence[Consignment]) -> Network:
    return replace(network, consignments=tuple(consignments))


def iter_classes(network: Network) -> Iterable[str]:
    return sorted({c.temp_class for c in network.consignments})

