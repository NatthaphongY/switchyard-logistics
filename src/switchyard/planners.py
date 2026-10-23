"""Two planners and a safe composition rule.

`plan_greedy` reproduces current practice: consignment by consignment, cheapest
lane set, capacity checked only while the leg is being booked. `plan_priced`
is the reference implementation: it prices congestion from load, prices thermal
risk by forbidding uncontrolled lanes unless the excursion allowance pays for
them, reserves handoff slack, and schedules the least-slack consignment first.

The composition rule is the commercial claim in engineering form: the shipped
plan is never worse than the baseline on (blocks, unsafe actions, excursion, cost),
because the baseline is always a candidate. Any measured separation therefore
comes from the algorithm, not from a straw man.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Dict, List, Optional, Sequence, Tuple

from .gate import Release, eligible_edges, evaluate
from .graph import max_flow, min_cost_flow, shortest_path
from .model import (
    AMBIENT,
    Consignment,
    Lane,
    LegPlan,
    Network,
    Plan,
    Thresholds,
)
from .physics import (
    availability_permille,
    physics,
    quantise,
    thermal_dose_permille,
)


def _leg_cost(network: Network, plan: Plan, cid: str) -> float:
    qty = network.consignment(cid).qty
    return sum(qty * network.lane(leg.lane).cost_per_unit for leg in plan.legs_of(cid))


# Price list as data. Each row returns the cost of one remedy for one
# consignment; boolean flags multiply, so no branch decides which price applies.
REMEDY_COST = (
    lambda net, plan, c, cfg: c.qty
    * float(cfg["pre_cool_per_unit"])
    * bool(plan.pre_cool_verified.get(c.id, False) and c.needs_cold_chain),
    lambda net, plan, c, cfg: c.qty
    * float(cfg["pre_authorisation_per_unit"])
    * plan.pre_authorised,
    lambda net, plan, c, cfg: c.value_usd
    * float(cfg["escrow_permille_of_value"])
    / 1000.0
    * (c.id in plan.escrowed),
    lambda net, plan, c, cfg: c.qty
    * float(cfg["thermal_protection_per_unit"])
    * (c.id in plan.thermal_protection),
    lambda net, plan, c, cfg: plan.prepositioned.get(c.id, 0.0)
    * float(cfg["preposition_per_unit"]),
    lambda net, plan, c, cfg: c.qty
    * float(cfg["deferral_per_unit"])
    * (c.id in plan.deferred),
    lambda net, plan, c, cfg: _leg_cost(net, plan, c.id)
    * float(cfg["backup_mode_permille_of_leg"])
    / 1000.0
    * (c.id in plan.backup_modes),
)

# Plan-level remedies: (flag, price key). One loop, no ladder.
PLAN_REMEDY_COST = (
    ("input_refreshed", "refresh_feed_min"),
    ("capacity_measured", "capacity_measure_min"),
    ("out_of_band_verified", "out_of_band_verify_min"),
)
PLAN_REMEDY_HOURLY = 0.5


def _remedy_cost(network: Network, plan: Plan) -> float:
    """Price every compliance action, so a lower unsafe-action count is never free."""
    cfg = physics().cost
    total = sum(
        row(network, plan, consignment, cfg)
        for row in REMEDY_COST
        for consignment in network.consignments
    )
    total += sum(
        float(cfg[key]) * PLAN_REMEDY_HOURLY
        for flag, key in PLAN_REMEDY_COST
        if getattr(plan, flag)
    )
    return total


def plan_cost(network: Network, plan: Plan) -> float:
    total = 0.0
    for leg in plan.legs:
        consignment = network.consignment(leg.consignment)
        total += consignment.qty * network.lane(leg.lane).cost_per_unit
    return total + _remedy_cost(network, plan)


# Strict-mode filters as data: a lane is usable in strict mode only when every
# predicate holds. This replaced a six-line if-ladder inside the edge builder.
STRICT_FILTERS = (
    lambda net, lane: lane.capacity_per_hour > 0,
    lambda net, lane: lane.monitored,
    lambda net, lane: net.nodes[lane.src].assessed and net.nodes[lane.dst].assessed,
    lambda net, lane: net.nodes[lane.src].capacity_per_hour > 0
    and net.nodes[lane.dst].capacity_per_hour > 0,
)


def _usable_edges(
    network: Network,
    temp_class: str,
    allow_uncontrolled: bool = False,
    exclude_cross_border: bool = False,
    strict: bool = False,
) -> List[Tuple[str, str, float, float]]:
    edges = []
    for lane in network.lanes:
        if exclude_cross_border and lane.cross_border:
            continue
        if strict and not all(check(network, lane) for check in STRICT_FILTERS):
            continue
        if temp_class != AMBIENT and not allow_uncontrolled and not lane.controlled:
            continue

        if temp_class != AMBIENT:
            if temp_class not in network.nodes[lane.src].classes:
                continue
            if temp_class not in network.nodes[lane.dst].classes:
                continue
        edges.append((lane.src, lane.dst, 1.0e9, lane.cost_per_unit))
    return edges


def _lane_load_slice(load: Dict[str, List[float]], lane: Lane, start: int, qty: float) -> None:
    first = int(start // 60)
    last = int((start + lane.travel_min) // 60)
    bucket = load.setdefault(lane.id, [])
    while len(bucket) <= last:
        bucket.append(0.0)
    for hour in range(first, last + 1):
        bucket[hour] += qty


def _fits(load: Dict[str, List[float]], lane: Lane, start: int, qty: float) -> bool:
    first = int(start // 60)
    last = int((start + lane.travel_min) // 60)
    bucket = load.get(lane.id, [])
    for hour in range(first, last + 1):
        used = bucket[hour] if hour < len(bucket) else 0.0
        if used + qty > lane.capacity_per_hour + 1e-9:
            return False
    return True


def _schedule_path(
    network: Network,
    consignment: Consignment,
    path: Sequence[str],
    load: Dict[str, List[float]],
    reserve_min: int,
) -> Optional[List[LegPlan]]:
    """Earliest feasible departure per leg, respecting capacity, blocks and the buffer."""
    legs: List[LegPlan] = []
    node = path[0]
    clock = consignment.ready_min
    deadline = consignment.due_min - reserve_min
    for index in range(1, len(path)):
        lane = next(
            (candidate for candidate in network.lanes if candidate.src == node and candidate.dst == path[index]),
            None,
        )
        if lane is None:
            return None
        start = max(clock, lane.blocked_until_min)
        latest = deadline - lane.travel_min
        chosen: Optional[int] = None
        candidate = start
        while candidate <= max(latest, start):
            if _fits(load, lane, candidate, consignment.qty):
                chosen = candidate
                break
            candidate += 15
        if chosen is None:
            return None
        _lane_load_slice(load, lane, chosen, consignment.qty)
        legs.append(
            LegPlan(
                consignment=consignment.id,
                lane=lane.id,
                depart_min=chosen,
                party=f"carrier:{lane.mode}",
                door_confirmed=True,
            )
        )
        clock = chosen + lane.travel_min
        node = path[index]
    if node != consignment.dest:
        return None
    return legs


def _assemble(
    network: Network,
    legs: Sequence[LegPlan],
    strategy: str,
    decision_age_min: int = 0,
) -> Plan:
    pre_cool = {c.id: True for c in network.consignments if c.needs_cold_chain}
    excursion = {}
    for consignment in network.consignments:
        total = 0
        for leg in [leg for leg in legs if leg.consignment == consignment.id]:
            lane = network.lane(leg.lane)
            if not lane.controlled and consignment.needs_cold_chain:
                total += lane.travel_min
        excursion[consignment.id] = total
    return Plan(
        legs=tuple(legs),
        decision_age_min=decision_age_min,
        pre_cool_verified=pre_cool,
        excursion_estimate_min=excursion,
        approvals_needed=0,
        strategy=strategy,
    )


def plan_greedy(network: Network, thresholds: Optional[Thresholds] = None) -> Plan:
    """Current practice: per consignment, cheapest lane set, earliest booking."""
    thresholds = thresholds or Thresholds()
    load: Dict[str, List[float]] = {}
    legs: List[LegPlan] = []
    order = sorted(network.consignments, key=lambda c: (c.due_min, c.id))
    for consignment in order:
        edges = _usable_edges(network, consignment.temp_class, allow_uncontrolled=True)
        path, _ = shortest_path(edges, consignment.origin, consignment.dest)
        if not path:
            continue
        scheduled = _schedule_path(network, consignment, path, load, reserve_min=0)
        if scheduled is None:
            from dataclasses import replace as _replace

            relaxed = _replace(consignment, due_min=network.horizon_min)
            scheduled = _schedule_path(network, relaxed, path, load, reserve_min=0)
        if scheduled:
            legs.extend(scheduled)
    return _assemble(network, legs, "greedy-cost", decision_age_min=0)


def _load_penalty(
    network: Network, load: Dict[str, List[float]], weight: float
) -> Dict[Tuple[str, str], float]:
    penalty: Dict[Tuple[str, str], float] = {}
    for lane in network.lanes:
        bucket = load.get(lane.id, [])
        peak = max(bucket) if bucket else 0.0
        utilisation = peak / lane.capacity_per_hour if lane.capacity_per_hour > 0 else 0.0
        if utilisation > 0:
            penalty[(lane.src, lane.dst)] = weight * utilisation * lane.cost_per_unit * 2.0
    return penalty


def _candidate_paths(
    network: Network,
    consignment: Consignment,
    penalty: Dict[Tuple[str, str], float],
    allow_uncontrolled: bool,
    limit: int = 4,
    exclude_cross_border: bool = False,
    strict: bool = False,
) -> List[List[str]]:
    """Deterministic path diversification by blocking the first edge of each hit."""
    edges = _usable_edges(
        network, consignment.temp_class, allow_uncontrolled, exclude_cross_border, strict
    )

    paths: List[List[str]] = []
    blocked: Dict[Tuple[str, str], float] = {}
    for _ in range(limit):
        weights = dict(penalty)
        weights.update(blocked)
        path, _ = shortest_path(edges, consignment.origin, consignment.dest, weights)
        if not path or path in paths or len(path) < 2:
            break
        paths.append(path)
        blocked[(path[0], path[1])] = 1.0e6
    return paths


def _excursion_of(
    network: Network, consignment: Consignment, legs: Sequence[LegPlan]
) -> int:
    total = 0
    previous_arrival: Optional[int] = None
    for leg in legs:
        lane = network.lane(leg.lane)
        if previous_arrival is not None:
            station = network.nodes[lane.src]
            if consignment.temp_class not in station.classes:
                total += max(0, leg.depart_min - previous_arrival)
        if not lane.controlled and consignment.needs_cold_chain:
            total += lane.travel_min
        previous_arrival = leg.depart_min + lane.travel_min
    return total


def _score_schedule(
    network: Network, consignment: Consignment, legs: Sequence[LegPlan]
) -> Tuple[int, int, float]:
    """Lexicographic: lateness minutes, excursion beyond allowance, transport cost."""
    arrival = legs[-1].depart_min + network.lane(legs[-1].lane).travel_min
    late = max(0, arrival - consignment.due_min)
    excursion = _excursion_of(network, consignment, legs)
    over = max(0, excursion - consignment.excursion_allowance_min)
    cost = sum(consignment.qty * network.lane(leg.lane).cost_per_unit for leg in legs)
    return late, over, round(cost, 6)


# Sequencing rules as data: each row produces a sort key for one consignment.
ORDER_KEYS = {
    "slack": lambda net, c, exclude: (c.due_min - c.ready_min, c.due_min, c.id),
    "constrained": lambda net, c, exclude: (
        len(_candidate_paths(net, c, {}, False, limit=2, exclude_cross_border=exclude)),
        c.due_min,
        c.id,
    ),
    "qty": lambda net, c, exclude: (-c.qty, c.due_min, c.id),
}


def _priced_once(
    network: Network,
    thresholds: Thresholds,
    weight: float,
    order: str,
    exclude_cross_border: bool = False,
) -> Plan:
    load: Dict[str, List[float]] = {}
    legs: List[LegPlan] = []
    order_key = ORDER_KEYS[order]
    sequence = sorted(
        network.consignments, key=lambda c: order_key(network, c, exclude_cross_border)
    )

    for consignment in sequence:
        penalty = _load_penalty(network, load, weight)
        candidates: List[Tuple[Tuple[int, int, float], List[LegPlan]]] = []
        pools = [False]
        if consignment.excursion_allowance_min > 0:
            pools.append(True)
        for allow_uncontrolled in pools:
            for path in _candidate_paths(
                network, consignment, penalty, allow_uncontrolled,
                exclude_cross_border=exclude_cross_border,
            ):

                for reserve in (thresholds.handoff_max_min, 0):
                    scheduled = _schedule_path(network, consignment, path, load, reserve_min=reserve)
                    if scheduled:
                        candidates.append((_score_schedule(network, consignment, scheduled), scheduled))
                        break
        if not candidates:
            continue
        candidates.sort(key=lambda item: item[0])
        legs.extend(candidates[0][1])
    return _assemble(network, legs, f"priced-{order}-lambda-{weight:g}", decision_age_min=0)



def plan_priced(
    network: Network,
    thresholds: Optional[Thresholds] = None,
    weights: Sequence[float] = (0.5, 2.0),
    orders: Sequence[str] = ("slack", "constrained", "qty"),
    event: Optional[dict] = None,
) -> Tuple[Plan, Release]:
    thresholds = thresholds or Thresholds()
    catalysts = (event or {}).get("catalysts", {})
    exclude = bool(catalysts.get("geoeconomic", {}).get("export_control", False))
    best: Optional[Tuple[Tuple[int, int, int, float], Plan, Release]] = None
    for weight in weights:
        for order in orders:
            candidate = _priced_once(network, thresholds, weight, order, exclude_cross_border=exclude)

            release = evaluate(network, candidate, event, thresholds)
            key = (
                release.blocks,
                release.unsafe_control_actions,
                release.excursion_total,
                round(plan_cost(network, candidate), 6),
            )
            if best is None or key < best[0]:
                best = (key, candidate, release)
    assert best is not None
    return best[1], best[2]



def plan_with_composition(
    network: Network,
    event: Optional[dict] = None,
    thresholds: Optional[Thresholds] = None,
) -> Tuple[Plan, Release]:
    """Ship the best of baseline, generation one and generation two.

    The baseline is always a candidate, so the shipped plan can never be worse
    than current practice under the gate's own ordering. That is the composition
    rule from SW-02 section 6, extended to three candidates.
    """
    thresholds = thresholds or Thresholds()
    candidates: List[Tuple[Release, Plan]] = []

    base = plan_greedy(network, thresholds)
    candidates.append((evaluate(network, base, event, thresholds), base))

    priced, _ = plan_priced(network, thresholds, event=event)
    candidates.append((evaluate(network, priced, event, thresholds), priced))

    remedied = plan_remedied(network, thresholds, event=event)
    candidates.append((evaluate(network, remedied, event, thresholds), remedied))

    candidates.sort(
        key=lambda pair: (
            pair[0].blocks,
            pair[0].unsafe_control_actions,
            pair[0].excursion_total,
            round(plan_cost(network, pair[1]), 6),
        )
    )
    release, plan = candidates[0]
    return plan, release


def min_cost_lower_bound(network: Network) -> float:
    """LP relaxation of the multi-consignment problem, used only as a reported bound."""
    total = 0.0
    for consignment in network.consignments:
        edges = _usable_edges(network, consignment.temp_class, allow_uncontrolled=False)
        if not edges:
            continue
        cost, shipped, _, _ = min_cost_flow(edges, consignment.origin, consignment.dest, consignment.qty)
        if shipped + 1e-9 >= consignment.qty:
            total += cost
    return total


# Which remedies the event forces. Data, not branches: a new catalyst axis is a
# new row, and the planner picks it up without touching the loop below.
REMEDY_TRIGGERS = (
    ("escrow", lambda ev, fin, geo, cyber: float(fin.get("solvency_score", 1.0)) < 0.5),
    ("out_of_band_verify", lambda ev, fin, geo, cyber: bool(cyber.get("intrusion", False))),
    ("refresh_feed", lambda ev, fin, geo, cyber: ev.get("information_state") == "stale"),
    (
        "capacity_measure",
        lambda ev, fin, geo, cyber: ev.get("information_state") == "contradictory",
    ),
    (
        "pre_authorisation",
        lambda ev, fin, geo, cyber: ev.get("regulatory_gate", "none") != "none",
    ),
    (
        "avoid_cross_border",
        lambda ev, fin, geo, cyber: bool(geo.get("export_control", False)),
    ),
)


def _physics_penalty(
    network: Network,
    consignment: Consignment,
    legs: Sequence[LegPlan],
    thresholds: Thresholds,
    protected: bool,
) -> Tuple[int, int, int, float]:
    """Lexicographic score used by the remedied planner.

    Lateness first (a plan that misses the window is not a plan), then thermal
    dose above the quality budget, then availability shortfall, then cost. The
    order is fixed and published, so the planner cannot quietly trade safety for
    money.
    """
    arrival = legs[-1].depart_min + network.lane(legs[-1].lane).travel_min
    late = max(0, arrival - consignment.due_min)
    excursion = _excursion_of(network, consignment, legs)
    dose = thermal_dose_permille(
        excursion,
        consignment.heat_gain_permille,
        protected,
        int(physics().thermal["protection_credit_permille"]),
        consignment.quality_budget_min,
    )
    over_dose = max(0, dose - thresholds.thermal_budget_permille)
    modes = [network.lane(leg.lane).mode for leg in legs]
    availability = availability_permille(modes, physics().mode_availability)
    shortfall = max(0, thresholds.availability_floor_permille - availability)
    cost = sum(consignment.qty * network.lane(leg.lane).cost_per_unit for leg in legs)
    # Dose is ranked as a magnitude, not only when it breaches the budget: two
    # routes can both be legal and still differ by a factor of three in potency
    # lost, and the planner is supposed to prefer the cheaper one in that sense.
    return late, dose, shortfall, round(cost, 6)


def plan_remedied(
    network: Network,
    thresholds: Optional[Thresholds] = None,
    event: Optional[dict] = None,
    disable: Sequence[str] = (),
) -> Plan:
    """Reference planner, generation two.

    Generation one (`plan_priced`) prices congestion and thermal risk. Generation
    two additionally executes every remedy the gate can demand, and pays for each
    one: pre-authorisation, feed refresh, capacity measurement, out-of-band
    document verification, escrow, a backup mode, active cooling and forward
    stock. It also refuses to route through stations that are already saturated,
    unmonitored, dead or unassessed, unless there is no alternative at all.

    Nothing here is a shortcut around the gate: the same `evaluate` function
    scores the result, and the composition rule keeps the baseline in the running.
    """
    thresholds = thresholds or Thresholds()
    event = event or {}
    catalysts = event.get("catalysts", {})
    geo = catalysts.get("geoeconomic", {})
    cyber = catalysts.get("cyber", {})
    financial = catalysts.get("financial", {})
    config = physics()

    exclude_border = bool(geo.get("export_control", False))
    blocked = frozenset(disable)
    blocked_modes = {lane.mode for lane in network.lanes if lane.blocked_until_min > 0}
    all_modes = sorted({lane.mode for lane in network.lanes})

    load: Dict[str, List[float]] = {}
    legs: List[LegPlan] = []
    escrowed: List[str] = []
    backup_modes: Dict[str, str] = {}
    protected: List[str] = []
    prepositioned: Dict[str, float] = {}
    deferred: List[str] = []
    remedies = set()

    remedies = {
        name
        for name, test in REMEDY_TRIGGERS
        if name not in disable and test(event, financial, geo, cyber)
    }
    escrowed = [c.id for c in network.consignments] * int("escrow" in remedies)

    total_qty = sum(c.qty for c in network.consignments) or 1.0
    committed = 0.0
    deferred_qty = 0.0
    floor_qty = thresholds.service_floor_permille * total_qty / 1000.0
    order = sorted(network.consignments, key=lambda c: (-c.criticality, c.due_min, c.id))
    for consignment in order:
        cid = consignment.id
        candidate_paths = _candidate_paths(
            network, consignment, {}, False, limit=4,
            exclude_cross_border=exclude_border, strict=True,
        )
        strict = bool(candidate_paths)
        if not candidate_paths:
            remedies.add("fallback_graph")
            candidate_paths = _candidate_paths(
                network, consignment, {}, False, limit=4,
                exclude_cross_border=exclude_border, strict=False,
            )
        if not candidate_paths:
            candidate_paths = _candidate_paths(
                network, consignment, {}, True, limit=4,
                exclude_cross_border=exclude_border, strict=False,
            )

        best: Optional[Tuple[Tuple[int, int, int, float], List[str], List[LegPlan]]] = None
        for path in candidate_paths:
            for reserve in (thresholds.handoff_max_min, 0):
                scratch = {key: list(values) for key, values in load.items()}
                scheduled = _schedule_path(network, consignment, path, scratch, reserve_min=reserve)
                if not scheduled:
                    continue
                score = _physics_penalty(network, consignment, scheduled, thresholds, False)
                if best is None or score < best[0]:
                    best = (score, list(path), scheduled)

        if best is None:
            remaining = total_qty - committed - deferred_qty - consignment.qty
            relaxed = replace(consignment, due_min=network.horizon_min)
            if (
                consignment.criticality <= 1
                and remaining + 1e-9 >= floor_qty
                and "triage_defer" not in blocked
            ):
                deferred.append(cid)
                deferred_qty += consignment.qty
                remedies.add("triage_defer")
                continue
            for path in candidate_paths:
                scratch = {key: list(values) for key, values in load.items()}
                scheduled = _schedule_path(network, relaxed, path, scratch, reserve_min=0)
                if not scheduled:
                    continue
                score = _physics_penalty(network, relaxed, scheduled, thresholds, False)
                if best is None or score < best[0]:
                    best = (score, list(path), scheduled)
        if best is None:
            # Unroutable, not deferred: the network cannot move it, which is a
            # GATE-FLOW-001 fact, not a service trade the planner chose.
            continue

        _, chosen_path, scheduled = best
        if scheduled[0].depart_min > consignment.ready_min and consignment.criticality >= 2:
            remedies.add("reserve_slot")

        # Refuse cargo that the projection says will be destroyed. Deferral is
        # bounded by the service floor, so this can never become an excuse to
        # ship nothing: the floor is checked before the trade is made.
        projected = _physics_penalty(network, consignment, scheduled, thresholds, False)
        abandon = int(physics().thermal["abandon_threshold_permille"])
        if (
            projected[1] > abandon
            and consignment.criticality <= 1
            and "triage_defer" not in blocked
            and total_qty - committed - deferred_qty - consignment.qty + 1e-9 >= floor_qty
        ):
            deferred.append(cid)
            deferred_qty += consignment.qty
            remedies.add("triage_defer")
            continue

        # Active cooling is bought only when the dose actually demands it, and
        # only when the credit is enough to bring the dose under the budget.
        score = _physics_penalty(network, consignment, scheduled, thresholds, False)
        threshold = int(physics().thermal["protection_threshold_permille"])
        if score[1] > threshold and "active_cooling" not in blocked:
            protected_score = _physics_penalty(network, consignment, scheduled, thresholds, True)
            if protected_score[1] < score[1]:
                protected.append(cid)
                remedies.add("active_cooling")

        # Forward stock is committed only for the part the network cannot move.
        if consignment.prepositioned_qty > 0 and "preposition" not in blocked:
            window = max(60, consignment.due_min - consignment.ready_min)
            edges = eligible_edges(network, consignment.temp_class, window)
            shipped, _ = max_flow(edges, consignment.origin, consignment.dest)
            shortage = quantise(consignment.qty) - shipped
            if shortage > 0:
                prepositioned[cid] = min(
                    consignment.prepositioned_qty, round(shortage / 1_000_000, 6)
                )
                remedies.add("preposition")

        if len({network.lane(leg.lane).mode for leg in scheduled}) == 1 and "backup_mode" not in blocked:
            used = network.lane(scheduled[0].lane).mode
            if used in blocked_modes:
                alternatives = [
                    mode for mode in all_modes
                    if mode != used and mode not in blocked_modes
                ]
                if alternatives:
                    backup_modes[cid] = max(
                        alternatives, key=lambda m: (config.mode_availability.get(m, 0), m)
                    )
                    remedies.add("backup_mode")

        # Commit: re-run the schedule against the real load so reservations are
        # counted exactly once, then append the legs.
        committed_legs = _schedule_path(
            network, consignment, chosen_path, load, reserve_min=thresholds.handoff_max_min
        )
        if committed_legs is None:
            committed_legs = scheduled
            for leg in committed_legs:
                _lane_load_slice(load, network.lane(leg.lane), leg.depart_min, consignment.qty)
        legs.extend(committed_legs)
        committed += consignment.qty
        if strict:
            remedies.add("strict_graph")

    plan = _assemble(network, legs, f"remedied-{len(remedies)}", decision_age_min=0)
    return replace(
        plan,
        pre_authorised="pre_authorisation" in remedies,
        input_refreshed="refresh_feed" in remedies,
        capacity_measured="capacity_measure" in remedies,
        out_of_band_verified="out_of_band_verify" in remedies,
        escrowed=tuple(sorted(escrowed)),
        backup_modes=dict(sorted(backup_modes.items())),
        thermal_protection=tuple(sorted(protected)),
        prepositioned=dict(sorted(prepositioned.items())),
        deferred=tuple(sorted(deferred)),
        remedies=tuple(sorted(remedies)),
    )

