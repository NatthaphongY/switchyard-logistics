"""Cascade model: a disruption propagates, it does not stay where it started.

Three imported mechanisms, each with a stated domain and a stated limit:

  1. Branching process, from nuclear chain-reaction theory: each active disruption
     produces a random number of offspring with mean k_eff. k_eff below one
     decays, above one avalanches. The number is computed from topology, not
     asserted: k_eff = fanout x susceptibility, where susceptibility falls as
     alternative lanes per node and monitoring coverage rise.
  2. Percolation, from statistical physics: after the cascade, the largest
     connected component of the class-eligible graph is measured. A drop marks a
     network that has fragmented rather than merely slowed.
  3. Delayed response, from reactor kinetics: repairs arrive after a delay, so a
     fraction of capacity is restored late rather than not at all. That delay is
     what a replanner can exploit and a fixed plan cannot.

Limits, stated rather than hidden: k_eff is a design assumption calibrated on
synthetic topology. It is not an empirical estimate for any real corridor, and the
programme does not claim that it is.
"""

from __future__ import annotations

import math
from .rng import StreamRandom
from dataclasses import replace
from typing import Dict, List, Optional, Tuple

from .model import Lane, Network, Node

DAMPING = 0.6


def out_degree(network: Network) -> float:
    return len(network.lanes) / max(1, len(network.nodes))


def monitoring_coverage(network: Network) -> float:
    if not network.lanes:
        return 0.0
    return sum(1 for lane in network.lanes if lane.monitored) / len(network.lanes)


def susceptibility(network: Network) -> float:
    redundancy = max(1.0, out_degree(network) - 1.0)
    return (1.0 / redundancy) * (1.15 - 0.3 * monitoring_coverage(network))


def effective_reproduction(network: Network, fanout: float) -> float:
    return fanout * susceptibility(network)


def _offspring(k_eff: float, rng: StreamRandom) -> int:
    if k_eff <= 0:
        return 0
    whole = int(math.floor(k_eff))
    count = whole + (1 if rng.random() < (k_eff - whole) else 0)
    return max(0, min(count, 3))


def giant_component(network: Network, temp_class: str) -> float:
    """Largest connected component of the eligible graph, as a fraction of nodes."""
    parent: Dict[str, str] = {nid: nid for nid in network.nodes}

    def find(node: str) -> str:
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)

    for lane in network.lanes:
        if lane.capacity_per_hour <= 0:
            continue
        if temp_class != "ambient":
            if not lane.controlled:
                continue
            if temp_class not in network.nodes[lane.src].classes:
                continue
            if temp_class not in network.nodes[lane.dst].classes:
                continue
        union(lane.src, lane.dst)
    sizes: Dict[str, int] = {}
    for nid in network.nodes:
        root = find(nid)
        sizes[root] = sizes.get(root, 0) + 1
    return max(sizes.values()) / max(1, len(network.nodes))


def catalyst_pressure(event: dict) -> float:
    """Four structural catalysts, each normalised to [0, 1].

    geoeconomic: export control counts as fully open, otherwise the tariff step
    relative to 35 percent.
    labour: an actual action counts as fully open, otherwise the vulnerability
    index.
    financial: default counts as fully open, otherwise one minus the solvency
    score.
    cyber: an intrusion counts as fully open, otherwise half the digital
    dependency, because dependency without an intrusion only raises exposure.

    These weights are programme decisions, stated so they can be argued with.
    """
    catalysts = event.get("catalysts", {})
    geo = catalysts.get("geoeconomic", {})
    labour = catalysts.get("labour", {})
    financial = catalysts.get("financial", {})
    cyber = catalysts.get("cyber", {})
    values = [
        1.0 if geo.get("export_control") else min(1.0, float(geo.get("tariff_shock_pct", 0.0)) / 0.35),
        1.0 if labour.get("action") else float(labour.get("vulnerability_index", 0.0)),
        1.0 if financial.get("default") else 1.0 - float(financial.get("solvency_score", 1.0)),
        1.0 if cyber.get("intrusion") else 0.5 * float(cyber.get("digital_dependency", 0.0)),
    ]
    return sum(values) / len(values)


def propagate(
    network: Network,
    event: dict,
    seed: int,
    max_depth: int = 4,
) -> Tuple[Network, dict]:
    """Apply secondary disruptions along the topology, generation by generation."""
    rng = StreamRandom(seed ^ 0xC0FFEE)
    fanout = float(event.get("cascade_fanout", 1.0))
    depth_limit = int(event.get("propagation_depth", max_depth))
    repair_delay = int(event.get("repair_delay_min", 240))
    pressure = catalyst_pressure(event)
    k_eff = effective_reproduction(network, fanout) * (1.0 + pressure)


    lanes: List[Lane] = list(network.lanes)
    nodes: Dict[str, Node] = dict(network.nodes)
    adjacent = {
        index: [
            other for other in range(len(lanes))
            if other != index and ({lanes[index].src, lanes[index].dst} & {lanes[other].src, lanes[other].dst})
        ]
        for index in range(len(lanes))
    }
    position = {lane.id: index for index, lane in enumerate(lanes)}
    seeds = [lane.id for lane in lanes if lane.blocked_until_min > 0 or lane.capacity_per_hour <= 0]
    if not seeds:
        seeds = [lanes[0].id] if lanes else []
    active = [position[lane_id] for lane_id in seeds]
    generations: List[int] = []
    total_hits = 0
    delayed_capacity = 0.0
    for generation in range(1, depth_limit + 1):
        strength = DAMPING ** (generation - 1)
        next_active: List[int] = []
        hits = 0
        for lane_index in active:
            neighbours = adjacent[lane_index]
            for _ in range(_offspring(k_eff, rng)):
                if not neighbours:
                    break
                victim_index = neighbours[rng.below(len(neighbours))]
                victim = lanes[victim_index]
                loss = min(0.8, 0.45 * strength)
                capacity = max(0.0, victim.capacity_per_hour * (1.0 - loss))
                lanes[victim_index] = replace(
                    victim,
                    capacity_per_hour=round(capacity, 3),
                    travel_min=int(round(victim.travel_min * (1.0 + 0.25 * strength))),
                    cost_per_unit=round(victim.cost_per_unit * (1.0 + 0.15 * strength), 3),
                    monitored=victim.monitored and rng.random() > 0.25 * strength,
                    blocked_until_min=max(
                        victim.blocked_until_min,
                        int(repair_delay * strength) if rng.random() < 0.25 else 0,
                    ),
                )
                next_active.append(victim_index)
                hits += 1
                delayed_capacity += capacity

        generations.append(hits)
        total_hits += hits
        active = sorted(set(next_active))
        if not active:
            break

    cascaded = Network(
        name=network.name,
        horizon_min=network.horizon_min,
        nodes=nodes,
        lanes=tuple(lanes),
        consignments=network.consignments,
    )
    telemetry = {
        "k_eff": round(k_eff, 3),
        "supercritical": k_eff > 1.0,
        "catalyst_pressure": round(pressure, 3),
        "generations": generations,
        "secondary_hits": total_hits,
        "susceptibility": round(susceptibility(network), 3),
        "out_degree": round(out_degree(network), 3),
        "monitoring_coverage": round(monitoring_coverage(network), 3),
        "giant_component_ambient": round(giant_component(cascaded, "ambient"), 3),
        "giant_component_cold": round(giant_component(cascaded, "chilled"), 3),
        "repair_delay_min": repair_delay,
        "delayed_capacity": round(delayed_capacity, 2),
    }
    return cascaded, telemetry
