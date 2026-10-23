"""Synthetic scenario generator over the six event axes (BHR-RS-06 section 3).

The generator is seeded and versioned. A scenario is a network plus an event
vector; the same seed always produces the same bytes, so an external party can
reproduce every number in the report (gate B5).

Events are data. No branch in the gate or the planners reads an event name.
"""

from __future__ import annotations

from .rng import StreamRandom
from dataclasses import replace
from typing import List, Tuple

from .model import Lane, Network, Node, Consignment, with_consignments, with_lanes
from .graph import shortest_path

MODES = ("road", "rail", "sea", "air")

# Onset damping and structural block length as data (no onset ladder).
ONSET_FACTOR = {"instant": 1.0, "gradual": 0.5}
HORIZON_BLOCK_MIN = {
    "structural": 720,
    "hours": 90,
    "days": 90,
    "weeks": 240,
    "months": 240,
}

# Which lanes and nodes a scope touches, and whether the scope can break
# control or assessment. One table per question, so the event model has no
# ladder over scope names.
SCOPE_HITS_LANE = {
    "global": lambda net, ctx, lane: True,
    "region": lambda net, ctx, lane: net.nodes[lane.src].region == ctx["region"],
    "lane": lambda net, ctx, lane: lane.id == ctx["lane"],
    "node": lambda net, ctx, lane: lane.src == ctx["node"] or lane.dst == ctx["node"],
}
SCOPE_NODES = {
    "global": lambda nodes, ctx: sorted(nodes),
    "region": lambda nodes, ctx: [
        nid for nid, node in nodes.items() if node.region == ctx["region"]
    ],
    "node": lambda nodes, ctx: [ctx["node"]],
    "lane": lambda nodes, ctx: [],
}
SCOPE_BLOCKS_STRUCTURALLY = frozenset({"global", "region"})
SCOPE_CAN_BREAK_CONTROL = frozenset({"lane", "node", "region"})

# Facility classes by node kind: 0 = dry, 1 = chilled chain, 2 = frozen capable.
CLASSES_BY_KIND = {
    0: ("ambient",),
    1: ("ambient", "chilled"),
    2: ("ambient", "chilled", "frozen"),
}

# Thermal profile by class: insulation-dependent heat gain and the quality
# budget that dose is measured against. Data, not branches.
THERMAL_PROFILE = {
    "frozen": {"heat": (1150, 1250, 1350, 1400), "budget": (90, 120, 150), "allowance": (0,)},
    "chilled": {"heat": (900, 1000, 1100, 1200), "budget": (180, 210, 240), "allowance": (0, 15, 30)},
    "ambient": {"heat": (700, 750, 800), "budget": (240, 300, 360), "allowance": (0, 15, 30)},
}


def _node(rng: StreamRandom, index: int, classes: Tuple[str, ...]) -> Node:
    return Node(
        id=f"N{index:02d}",
        region=f"R{index % 3}",
        classes=classes,
        dwell_p95_min=rng.choice((90, 120, 180, 240)),
        capacity_per_hour=float(rng.choice((20, 40, 60, 120))),
        assessed=True,
    )


def _cold(nodes: dict) -> set:
    return {nid for nid, node in nodes.items() if "chilled" in node.classes}


def _travel(lanes: List[Lane], nodes: dict, origin: str, dest: str, temp_class: str) -> float:
    edges = []
    for lane in lanes:
        if temp_class != "ambient":
            if not lane.controlled:
                continue
            if temp_class not in nodes[lane.src].classes or temp_class not in nodes[lane.dst].classes:
                continue
        edges.append((lane.src, lane.dst, 1.0, float(lane.travel_min)))
    path, distance = shortest_path(edges, origin, dest)
    return distance if path else float("inf")


def make_network(seed: int, node_count: int = 10, consignment_count: int = 8) -> Network:
    rng = StreamRandom(seed)
    nodes = {}
    cold_nodes = [index for index in range(node_count) if index % 3 == 0]
    frozen_nodes = [index for index in range(node_count) if index % 6 == 0]
    for index in range(node_count):
        kind = 2 * int(index in frozen_nodes) + int(
            index in cold_nodes and index not in frozen_nodes
        )
        classes = CLASSES_BY_KIND[kind]
        nodes[f"N{index:02d}"] = _node(rng, index, classes)

    lanes: List[Lane] = []
    pair_index = 0
    for index in range(node_count):
        for step in (1, 2, 3):
            target = (index + step) % node_count
            if target == index:
                continue
            mode = MODES[(index + step) % len(MODES)]
            travel = {
                "road": rng.randint(45, 150),
                "rail": rng.randint(90, 240),
                "sea": rng.randint(240, 600),
                "air": rng.randint(30, 90),
            }[mode]
            cost = {
                "road": rng.uniform(0.8, 1.6),
                "rail": rng.uniform(0.5, 1.1),
                "sea": rng.uniform(0.3, 0.8),
                "air": rng.uniform(2.4, 4.2),
            }[mode]
            capacity = {
                "road": rng.choice((10.0, 20.0, 30.0)),
                "rail": rng.choice((20.0, 40.0)),
                "sea": rng.choice((30.0, 60.0)),
                "air": rng.choice((5.0, 10.0)),
            }[mode]
            lanes.append(
                Lane(
                    id=f"L{pair_index:03d}",
                    src=f"N{index:02d}",
                    dst=f"N{target:02d}",
                    mode=mode,
                    travel_min=travel,
                    capacity_per_hour=capacity,
                    cost_per_unit=round(cost, 3),
                    monitored=rng.random() > 0.15,
                    controlled=(
                        mode in ("rail", "sea")
                        or (f"N{index:02d}" in _cold(nodes) and f"N{target:02d}" in _cold(nodes))
                        or rng.random() > 0.5
                    ),
                    blocked_until_min=0,
                    cross_border=nodes[f"N{index:02d}"].region != nodes[f"N{target:02d}"].region,
                )
            )
            pair_index += 1

    for chain in (cold_nodes, frozen_nodes):
        for position, index in enumerate(chain):
            target = chain[(position + 1) % len(chain)]
            if target == index:
                continue
            lanes.append(
                Lane(
                    id=f"L{900 + pair_index:03d}",
                    src=f"N{index:02d}",
                    dst=f"N{target:02d}",
                    mode="rail" if chain is cold_nodes else "air",
                    travel_min=90 if chain is cold_nodes else 60,
                    capacity_per_hour=30.0 if chain is cold_nodes else 12.0,
                    cost_per_unit=0.9 if chain is cold_nodes else 3.2,
                    monitored=True,
                    controlled=True,
                )
            )
            pair_index += 1

    consignments: List[Consignment] = []
    cold_ids = sorted(_cold(nodes))
    frozen_ids = sorted(nid for nid, node in nodes.items() if "frozen" in node.classes)
    ambient_ids = sorted(nodes)
    for index in range(consignment_count):
        temp_class = rng.choices(
            ("ambient", "chilled", "frozen"), weights=(0.3, 0.45, 0.25)
        )[0]
        pool = ambient_ids if temp_class == "ambient" else (
            cold_ids if temp_class == "chilled" else frozen_ids
        )
        if len(pool) < 2:
            temp_class, pool = "ambient", ambient_ids
        origin = pool[rng.randrange(len(pool))]
        dest = pool[rng.randrange(len(pool))]
        while dest == origin:
            dest = pool[rng.randrange(len(pool))]
        travel = _travel(lanes, nodes, origin, dest, temp_class)
        if travel == float("inf"):
            continue
        ready = rng.choice((0, 30, 60, 120))
        window = max(rng.choice((360, 480, 600, 900)), int(travel * 2) + 120)
        qty = float(rng.choice((4, 6, 8, 10)))
        profile = THERMAL_PROFILE[temp_class]
        heat = rng.choice(profile["heat"])
        budget = rng.choice(profile["budget"])
        consignments.append(
            Consignment(
                id=f"C{index:02d}",
                origin=origin,
                dest=dest,
                qty=qty,
                temp_class=temp_class,
                ready_min=ready,
                due_min=ready + window,
                excursion_allowance_min=rng.choice(profile["allowance"]),
                heat_gain_permille=heat,
                quality_budget_min=budget,
                criticality=rng.choices((1, 2, 3), weights=(0.45, 0.35, 0.20))[0],
                value_usd=round(qty * rng.choice((800.0, 2500.0, 9000.0)), 2),
                # Forward stock that exists and could have been staged earlier.
                # The planner still has to commit to it, and pay for it.
                prepositioned_qty=0.0 if rng.random() > 0.45 else float(rng.choice((2, 4))),
            )
        )
    return Network(
        name=f"synthetic-{seed:05d}",
        horizon_min=1440,
        nodes=nodes,
        lanes=tuple(lanes),
        consignments=tuple(consignments),
    )


def sample_event(rng: StreamRandom, intensity: float = 1.0) -> dict:
    """Sample the six axes. Intensities above 1 stress the coupling term."""
    onset = rng.choices(("instant", "gradual"), weights=(0.55, 0.45))[0]
    notice = rng.choices((0, "hours", "days"), weights=(0.3, 0.45, 0.25))[0]
    duration = rng.choices(("hours", "days", "weeks", "months"), weights=(0.4, 0.35, 0.18, 0.07))[0]
    scope = rng.choices(("node", "lane", "region", "global"), weights=(0.2, 0.45, 0.25, 0.1))[0]
    reversibility = "structural" if duration in ("weeks", "months") else rng.choice(
        ("recoverable", "recoverable", "structural")
    )
    magnitude = {
        "capacity_loss": round(min(0.95, rng.uniform(0.1, 0.5) * intensity), 3),
        "lead_time_inflation": round(rng.uniform(0.05, 0.35) * intensity, 3),
        "cost_inflation": round(rng.uniform(0.02, 0.30) * intensity, 3),
    }
    return {
        "onset_rate": onset,
        "notice_min": notice,
        "duration": duration,
        "magnitude": magnitude,
        "scope": scope,
        "reversibility": reversibility,
        "cascade_fanout": round(rng.uniform(0.7, 1.5) * intensity, 3),
        "propagation_depth": rng.choice((2, 3, 4)),
        "repair_delay_min": rng.choice((120, 240, 480, 720)),
        "information_state": rng.choices(
            ("verified", "rumoured", "contradictory", "stale"), weights=(0.4, 0.25, 0.2, 0.15)
        )[0],
        "measurement_uncertainty": round(rng.uniform(0.02, 0.15), 3),
        "actor_response": rng.choices(
            ("cooperative", "opportunistic", "blocking"), weights=(0.55, 0.3, 0.15)
        )[0],
        "contract_regime": rng.choices(
            ("normal", "force_majeure", "penalty"), weights=(0.6, 0.25, 0.15)
        )[0],
        "regulatory_gate": rng.choices(
            ("none", "permit", "customs"), weights=(0.55, 0.3, 0.15)
        )[0],
        "catalysts": {
            "geoeconomic": {
                "tariff_shock_pct": round(rng.uniform(0.0, 0.35) * intensity, 3),
                "export_control": rng.random() < min(0.75, 0.25 * intensity),
                "permit_lead_h": rng.choice((24, 72, 168)),
            },
            "labour": {
                "vulnerability_index": round(rng.uniform(0.1, 0.9), 3),
                "action": rng.random() < min(0.6, 0.2 * intensity),
                "notice_min": rng.choice((0, 360, 1440)),
            },
            "financial": {
                "solvency_score": round(rng.uniform(0.15, 0.95), 3),
                "default": rng.random() < min(0.5, 0.15 * intensity),
                "payment_terms_days": rng.choice((30, 60, 90)),
            },
            "cyber": {
                "digital_dependency": round(rng.uniform(0.2, 0.95), 3),
                "intrusion": rng.random() < min(0.6, 0.2 * intensity),
                "recovery_h": rng.choice((12, 48, 120)),
            },
        },
    }



def apply_event(network: Network, event: dict, seed: int) -> Network:
    rng = StreamRandom(seed ^ 0x5EED)
    magnitude = event["magnitude"]
    loss = magnitude["capacity_loss"]
    inflation = magnitude["lead_time_inflation"]
    cost_inflation = magnitude["cost_inflation"]
    factor = ONSET_FACTOR[event["onset_rate"]]
    loss *= factor
    inflation *= factor
    scope = event["scope"]
    structural = event["reversibility"] == "structural"
    block_key = "structural" if structural else event["duration"]
    horizon_block = HORIZON_BLOCK_MIN[block_key]

    target_region = f"R{rng.randrange(3)}"
    target_lane = f"L{rng.randrange(len(network.lanes)):03d}"
    target_node = sorted(network.nodes)[rng.randrange(len(network.nodes))]
    context = {"region": target_region, "lane": target_lane, "node": target_node}
    hit = SCOPE_HITS_LANE[scope]

    lanes = []
    for lane in network.lanes:
        if not hit(network, context, lane):
            lanes.append(lane)
            continue
        capacity = max(0.0, lane.capacity_per_hour * (1.0 - loss))
        travel = int(round(lane.travel_min * (1.0 + inflation)))
        cost = round(lane.cost_per_unit * (1.0 + cost_inflation), 3)
        blocked = lane.blocked_until_min
        if structural and (scope in SCOPE_BLOCKS_STRUCTURALLY or lane.id == target_lane):
            blocked = max(blocked, horizon_block)
        roll = rng.random()
        flipped = roll < 0.10 and scope in SCOPE_CAN_BREAK_CONTROL
        lanes.append(
            replace(
                lane,
                travel_min=travel,
                capacity_per_hour=round(capacity, 3),
                cost_per_unit=cost,
                blocked_until_min=blocked,
                controlled=lane.controlled and not flipped,
            )
        )

    nodes = dict(network.nodes)
    for nid in SCOPE_NODES[scope](nodes, context):
        record = nodes[nid]
        nodes[nid] = replace(
            record,
            assessed=record.assessed and not (event["notice_min"] == 0 and nid == target_node),
            capacity_per_hour=round(max(1.0, record.capacity_per_hour * (1.0 - loss)), 3),
        )
    return Network(
        name=network.name,
        horizon_min=network.horizon_min,
        nodes=nodes,
        lanes=tuple(lanes),
        consignments=network.consignments,
    )


def scenario(seed: int, intensity: float = 1.0) -> Tuple[Network, dict]:
    rng = StreamRandom(seed)
    node_count = rng.choice((8, 10, 12))
    consignment_count = rng.choice((5, 8, 10))
    base = make_network(seed, node_count=node_count, consignment_count=consignment_count)
    event = sample_event(rng, intensity)
    primary = apply_event(base, event, seed)

    from .cascade import propagate

    cascaded, telemetry = propagate(primary, event, seed)
    event["cascade"] = telemetry

    lanes = list(cascaded.lanes)
    nodes = dict(cascaded.nodes)
    catalysts = event["catalysts"]
    geo = catalysts["geoeconomic"]
    labour = catalysts["labour"]
    financial = catalysts["financial"]
    cyber = catalysts["cyber"]

    if geo["tariff_shock_pct"] > 0:
        lanes = [
            replace(lane, cost_per_unit=round(lane.cost_per_unit * (1.0 + geo["tariff_shock_pct"]), 3))
            if lane.cross_border else lane
            for lane in lanes
        ]
    if geo["export_control"] and lanes:
        permit_block = int(geo["permit_lead_h"]) * 60
        lanes = [
            replace(lane, blocked_until_min=max(lane.blocked_until_min, permit_block))
            if lane.cross_border and (index % 2 == 0) else lane
            for index, lane in enumerate(lanes)
        ]
    if labour["action"] and nodes:
        node_id = sorted(nodes)[seed % len(nodes)]
        station = nodes[node_id]
        nodes[node_id] = replace(
            station,
            capacity_per_hour=0.0,
            dwell_p95_min=max(15, int(station.dwell_p95_min * 0.3)),
        )
    if financial["default"] and lanes:
        for offset in (0, 1):
            index = (seed + offset * 7) % len(lanes)
            lanes[index] = replace(lanes[index], capacity_per_hour=0.0)
    if cyber["intrusion"] and lanes:
        for offset in range(3):
            index = (seed + offset * 11) % len(lanes)
            lanes[index] = replace(lanes[index], monitored=False)
    network = Network(
        name=cascaded.name,
        horizon_min=cascaded.horizon_min,
        nodes=nodes,
        lanes=tuple(lanes),
        consignments=cascaded.consignments,
    )
    return network, event



