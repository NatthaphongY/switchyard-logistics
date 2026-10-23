"""Deterministic compliance gate (SW-06).

Implements the fourteen gate codes documented in SW-06 section 7. Every check
is a pure function of (network, plan, event vector, thresholds); no clock, no
randomness, no language model. A missing field produces a blocking finding rather
than a default (README section 3, item 7).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from .graph import max_flow
from .model import Network, Plan, Thresholds, plan_hash
from .physics import (
    availability_permille,
    physics,
    quantise,
    served_permille,
    thermal_dose_permille,
    utilisation_permille,
)

BLOCK = "block"
WARN = "warn"

# Comparison operators used by the physical rule table. Dispatch by name keeps
# the evaluator a single loop: no if-elif ladder decides which rule applies.
COMPARATORS = {
    "gt": lambda value, limit: value > limit,
    "ge": lambda value, limit: value >= limit,
    "lt": lambda value, limit: value < limit,
    "le": lambda value, limit: value <= limit,
}


@dataclass(frozen=True)
class PhysicalRule:
    """One row of the physical rule table (SW-11 section 6).

    The gate does not contain a branch per rule. It builds metrics, then applies
    every row through `COMPARATORS`. Adding a rule is adding a row, which is the
    same discipline the programme applies to prompts and to command words.
    """

    code: str
    scope: str
    metric: str
    comparator: str
    limit: str
    template: str


@dataclass(frozen=True)
class FlagRule:
    """A boolean gate rule as data: condition, location, message, all callables.

    Flag rules and physical rules both live in tables, so `evaluate` contains one
    loop per table instead of one branch per finding.
    """

    code: str
    scope: str
    condition: Callable[..., bool]
    location: Callable[..., str]
    message: Callable[..., str]


# Verdict precedence as data, highest severity first. The last row is total.
VERDICT_RULES = (
    (lambda findings: any(f.severity == BLOCK for f in findings), "BLOCKED"),
    (lambda findings: bool(findings), "PASS_WITH_CONDITION"),
    (lambda findings: True, "PASS"),
)


# Slack findings as data, in priority order: the first matching row reports.
# A ladder of `if`/`elif` here would mean the second condition had to know about
# the first; a table says that out loud.
SLACK_RULES = (
    (
        lambda slack, thresholds: slack <= 0,
        "GATE-SLACK-001",
        "slack {slack} min at arrival {arrival} against due {due}",
    ),
    (
        lambda slack, thresholds: slack < thresholds.handoff_max_min,
        "GATE-SLACK-002",
        "slack {slack} min below handoff budget {budget} min",
    ),
)


# Which subjects a rule walks. A new scope is a new row, not a new branch.
RULE_SUBJECTS = {
    "consignment": lambda network: network.consignments,
    "plan": lambda network: (None,),
    "network": lambda network: (None,),
}


FLAG_RULES: Tuple[FlagRule, ...] = (
    FlagRule(
        code="GATE-TEMP-002",
        scope="consignment",
        condition=lambda net, plan, c, ctx: c.needs_cold_chain
        and not plan.pre_cool_verified.get(c.id, False),
        location=lambda net, plan, c, ctx: c.origin,
        message=lambda net, plan, c, ctx: "pre-cooling not verified before release",
    ),
    FlagRule(
        code="GATE-HANDOFF-003",
        scope="consignment",
        condition=lambda net, plan, c, ctx: not plan.documents_verified,
        location=lambda net, plan, c, ctx: "custody records",
        message=lambda net, plan, c, ctx: (
            "handoff records cannot be verified against the system of record"
        ),
    ),
    FlagRule(
        code="GATE-PARTY-001",
        scope="consignment",
        condition=lambda net, plan, c, ctx: not plan.counterparty_verified
        and c.id not in plan.escrowed,
        location=lambda net, plan, c, ctx: "counterparty",
        message=lambda net, plan, c, ctx: (
            "counterparty solvency not verified for the legs of this consignment"
        ),
    ),
    FlagRule(
        code="GATE-DATA-001",
        scope="plan",
        condition=lambda net, plan, c, ctx: plan.decision_age_min > ctx["freshness"],
        location=lambda net, plan, c, ctx: "decision input",
        message=lambda net, plan, c, ctx: (
            f"input age {plan.decision_age_min} min above freshness limit "
            f"{ctx['freshness']} min"
        ),
    ),
    FlagRule(
        code="GATE-DATA-002",
        scope="plan",
        condition=lambda net, plan, c, ctx: not plan.capacity_verified,
        location=lambda net, plan, c, ctx: "capacity assumption",
        message=lambda net, plan, c, ctx: (
            "capacity assumption not verified, so the plan rests on an unmeasured quantity"
        ),
    ),
    FlagRule(
        code="GATE-PLAN-002",
        scope="plan",
        condition=lambda net, plan, c, ctx: ctx["notice_zero"] and plan.approvals_needed > 0,
        location=lambda net, plan, c, ctx: "approval path",
        message=lambda net, plan, c, ctx: (
            f"{plan.approvals_needed} approval step(s) required with zero notice"
        ),
    ),
)

PHYSICAL_RULES: Tuple[PhysicalRule, ...] = (
    PhysicalRule(
        code="GATE-QUEUE-001",
        scope="consignment",
        metric="queue_utilisation",
        comparator="gt",
        limit="queue_ceiling_permille",
        template=(
            "station {station} utilisation {value} permille above ceiling {limit}; "
            "delay factor {factor} permille of dwell"
        ),
    ),
    PhysicalRule(
        code="GATE-THERM-006",
        scope="consignment",
        metric="thermal_dose",
        comparator="gt",
        limit="thermal_budget_permille",
        template=(
            "thermal dose {value} permille of the quality budget above limit {limit}"
        ),
    ),
    PhysicalRule(
        code="GATE-RELIAB-001",
        scope="consignment",
        metric="availability",
        comparator="lt",
        limit="availability_floor_permille",
        template="series availability {value} permille below floor {limit} permille",
    ),
    PhysicalRule(
        code="GATE-SERVICE-001",
        scope="network",
        metric="served",
        comparator="lt",
        limit="service_floor_permille",
        template="deliberately deferred share leaves {value} permille served, below floor {limit}",
    ),
)

CODE_TO_UCA: Dict[str, Tuple[str, ...]] = {
    "GATE-TEMP-001": ("UCA4",),
    "GATE-TEMP-002": ("UCA1",),
    "GATE-TEMP-003": ("UCA3",),
    "GATE-TEMP-004": ("UCA6",),
    "GATE-TEMP-005": ("UCA6",),
    "GATE-SLACK-001": ("UCA2",),
    "GATE-SLACK-002": ("UCA2",),
    "GATE-FLOW-001": ("UCA9",),
    "GATE-HANDOFF-001": ("UCA11",),
    "GATE-HANDOFF-002": ("UCA7",),
    "GATE-DATA-001": ("UCA5",),
    "GATE-PLAN-001": ("UCA10",),
    "GATE-PLAN-002": ("UCA12",),
    "GATE-NODE-001": ("UCA8",),
    "GATE-MODE-001": ("UCA9",),
    "GATE-DATA-002": ("UCA5",),
    "GATE-LEGAL-001": ("UCA13",),
    "GATE-NODE-002": ("UCA14",),
    "GATE-PARTY-001": ("UCA15",),
    "GATE-HANDOFF-003": ("UCA16",),
    "GATE-QUEUE-001": ("UCA17",),
    "GATE-THERM-006": ("UCA18",),
    "GATE-RELIAB-001": ("UCA19",),
    "GATE-SERVICE-001": ("UCA20",),
}

REMEDY: Dict[str, str] = {
    "GATE-TEMP-001": "Split the consignment or change class",
    "GATE-TEMP-002": "Pre-cool and record the temperature before departure",
    "GATE-TEMP-003": "Add a logger or change the leg",
    "GATE-TEMP-004": "Pre-cool, change class, or reduce dwell",
    "GATE-TEMP-005": "Record a disposition or change the leg",
    "GATE-SLACK-001": "Shift departure or change mode",
    "GATE-SLACK-002": "Shift departure or reserve a slot",
    "GATE-FLOW-001": "Add capacity or reduce batch size",
    "GATE-HANDOFF-001": "Name the party and the handover time",
    "GATE-HANDOFF-002": "Confirm the receiving door",
    "GATE-DATA-001": "Refresh the input or replan",
    "GATE-PLAN-001": "Compute excursion before comparing cost",
    "GATE-PLAN-002": "Establish pre-authorisation",
    "GATE-NODE-001": "Assess the node or route through an assessed node",
    "GATE-MODE-001": "Hold capacity on a second mode",
    "GATE-DATA-002": "Verify the capacity assumption before release",
    "GATE-LEGAL-001": "Hold the permit or route through an uncontrolled border",
    "GATE-NODE-002": "Use a station with available throughput",
    "GATE-PARTY-001": "Verify counterparty solvency or escrow the leg",
    "GATE-HANDOFF-003": "Verify the handoff record out of band",
    "GATE-QUEUE-001": "Spread the load, add a server, or route through a station below the utilisation ceiling",
    "GATE-THERM-006": "Cut uncontrolled exposure, add active cooling, or reduce the batch",
    "GATE-RELIAB-001": "Book a backup mode or shorten the series route",
    "GATE-SERVICE-001": "Serve the floor before triaging low-criticality volume",
}


@dataclass(frozen=True)
class Finding:
    code: str
    severity: str
    consignment: str
    location: str
    measurement: str

    @property
    def remedy(self) -> str:
        return REMEDY[self.code]

    def as_dict(self) -> dict:
        return {
            "code": self.code,
            "severity": self.severity,
            "consignment": self.consignment,
            "location": self.location,
            "measurement": self.measurement,
            "remedy": self.remedy,
            "uca": list(CODE_TO_UCA[self.code]),
        }


@dataclass(frozen=True)
class Release:
    verdict: str
    findings: Tuple[Finding, ...]
    conditions: Tuple[str, ...]
    hash: str
    network: str
    strategy: str
    excursion_min: Dict[str, int]
    thermal_dose: Dict[str, int] = field(default_factory=dict)
    availability: Dict[str, int] = field(default_factory=dict)
    served: int = 1000

    @property
    def blocks(self) -> int:
        return sum(1 for f in self.findings if f.severity == BLOCK)

    @property
    def warns(self) -> int:
        return sum(1 for f in self.findings if f.severity == WARN)

    @property
    def unsafe_control_actions(self) -> int:
        """Counted per consignment and per action, not per code: one broken handoff in
        five consignments is five unsafe control actions, not one."""
        return len({(f.consignment, uca) for f in self.findings for uca in CODE_TO_UCA[f.code]})

    @property
    def distinct_uca_types(self) -> int:
        return len({uca for f in self.findings for uca in CODE_TO_UCA[f.code]})


    @property
    def total_findings(self) -> int:
        return len(self.findings)

    @property
    def excursion_total(self) -> int:
        return sum(self.excursion_min.values())

    def as_dict(self) -> dict:
        return {
            "verdict": self.verdict,
            "hash": self.hash,
            "network": self.network,
            "strategy": self.strategy,
            "blocks": self.blocks,
            "warns": self.warns,
            "unsafe_control_actions": self.unsafe_control_actions,
            "excursion_min": dict(sorted(self.excursion_min.items())),
            "thermal_dose": dict(sorted(self.thermal_dose.items())),
            "availability": dict(sorted(self.availability.items())),
            "served_permille": self.served,
            "conditions": list(self.conditions),
            "findings": [f.as_dict() for f in self.findings],
        }


def eligible_edges(network: Network, temp_class: str, window_min: int) -> list:
    """Capacities are converted to integer micro-units so that a second
    implementation in another language produces the identical maximum flow."""
    edges = []
    for lane in network.lanes:
        if temp_class != "ambient":
            if not lane.controlled:
                continue
            if temp_class not in network.nodes[lane.src].classes:
                continue
            if temp_class not in network.nodes[lane.dst].classes:
                continue
        capacity_micro = int(round(lane.capacity_per_hour * 1_000_000)) * max(window_min, 60) // 60
        if capacity_micro > 0:
            edges.append((lane.src, lane.dst, float(capacity_micro), lane.cost_per_unit))
    return edges



def evaluate(
    network: Network,
    plan: Plan,
    event: Optional[dict] = None,
    thresholds: Optional[Thresholds] = None,
) -> Release:
    thresholds = thresholds or Thresholds()
    event = event or {}
    findings: List[Finding] = []

    def add(code: str, consignment: str, location: str, measurement: str) -> None:
        severity = BLOCK if _is_block(code) else WARN
        findings.append(Finding(code, severity, consignment, location, measurement))

    excursion_min: Dict[str, int] = {}
    thermal: Dict[str, int] = {}
    available: Dict[str, int] = {}
    metrics: Dict[str, dict] = {}

    for consignment in network.consignments:
        cid = consignment.id
        legs = plan.legs_of(cid)
        if not legs:
            if cid not in plan.deferred:
                add("GATE-FLOW-001", cid, consignment.origin,
                    "no leg assigned to the consignment")
            excursion_min[cid] = 0
            continue
        node = consignment.origin
        previous_arrival: Optional[int] = None
        excursion = 0.0
        uncontrolled_legs = 0
        longest_uncontrolled = 0
        for leg in legs:
            lane = network.lane(leg.lane)
            if lane.src != node:
                add("GATE-HANDOFF-001", cid, node,
                    f"no custody link from {node} to {lane.src} before lane {lane.id}")
            if leg.depart_min < consignment.ready_min:
                add("GATE-SLACK-001", cid, lane.id,
                    f"departure {leg.depart_min} before cargo ready at {consignment.ready_min}")
            if leg.depart_min < lane.blocked_until_min:
                add("GATE-FLOW-001", cid, lane.id,
                    f"lane blocked until {lane.blocked_until_min}, departure {leg.depart_min}")
            if previous_arrival is not None:
                if leg.depart_min < previous_arrival:
                    add("GATE-HANDOFF-001", cid, node,
                        f"departure {leg.depart_min} before arrival {previous_arrival}")
                dwell = leg.depart_min - previous_arrival
                station = network.nodes[node]
                if dwell > station.dwell_p95_min:
                    add("GATE-SLACK-002", cid, node,
                        f"dwell {dwell} min above station p95 {station.dwell_p95_min} min")
                if consignment.needs_cold_chain and consignment.temp_class not in station.classes:
                    excursion += dwell
            if consignment.needs_cold_chain and not lane.controlled:
                excursion += lane.travel_min
                uncontrolled_legs += 1
                longest_uncontrolled = max(longest_uncontrolled, lane.travel_min)
            if not lane.monitored:
                add("GATE-TEMP-003", cid, lane.id, "no sensor coverage on the leg")
            if not network.nodes[lane.dst].assessed:
                add("GATE-NODE-001", cid, lane.dst, "backup node capacity not assessed")
            if (
                network.nodes[lane.src].capacity_per_hour <= 0
                or network.nodes[lane.dst].capacity_per_hour <= 0
            ):
                add("GATE-NODE-002", cid, lane.id, "station throughput unavailable at departure or arrival")
            if lane.cross_border and not plan.border_permits_held:
                add("GATE-LEGAL-001", cid, lane.id, "cross-border leg without a permit on file")
            if not leg.party:
                add("GATE-HANDOFF-001", cid, lane.id, "no accountable party for the leg")
            if not leg.door_confirmed:
                add("GATE-HANDOFF-002", cid, lane.dst, "receiving door not confirmed")
            previous_arrival = leg.depart_min + lane.travel_min
            node = lane.dst

        if node != consignment.dest:
            add("GATE-HANDOFF-001", cid, node,
                f"route terminates at {node} instead of {consignment.dest}")
        arrival = previous_arrival or 0
        slack = consignment.due_min - arrival
        for predicate, code, template in SLACK_RULES:
            if predicate(slack, thresholds):
                add(code, cid, consignment.dest,
                    template.format(slack=slack, arrival=arrival,
                                    due=consignment.due_min,
                                    budget=thresholds.handoff_max_min))
                break
        metrics.setdefault(cid, {})
        protected = cid in plan.thermal_protection
        dose = thermal_dose_permille(
            int(excursion),
            consignment.heat_gain_permille,
            protected,
            int(physics().thermal["protection_credit_permille"]),
            consignment.quality_budget_min,
        )
        thermal[cid] = dose
        modes = [network.lane(leg.lane).mode for leg in legs]
        availability = availability_permille(
            modes, physics().mode_availability, plan.backup_modes.get(cid)
        )
        available[cid] = availability
        metrics[cid]["thermal_dose"] = dose
        metrics[cid]["availability"] = availability

        if excursion > consignment.excursion_allowance_min:
            if not plan.excursion_disposition.get(cid, False):
                add("GATE-TEMP-005", cid, "route",
                    f"excursion {int(excursion)} min above allowance "
                    f"{consignment.excursion_allowance_min} min without disposition")
            if longest_uncontrolled > 180:
                add("GATE-TEMP-004", cid, "route",
                    f"uncontrolled leg of {longest_uncontrolled} min exceeds cooling capacity")
        if uncontrolled_legs and plan.excursion_estimate_min.get(cid) is None:
            if cid in plan.cost_reduction_accepted:
                add("GATE-PLAN-001", cid, "route",
                    "cost reduction accepted without recomputed excursion")
        window_min = max(60, consignment.due_min - consignment.ready_min)
        edges = eligible_edges(network, consignment.temp_class, window_min)
        shipped, cut = max_flow(edges, consignment.origin, consignment.dest)
        demand_micro = int(round(consignment.qty * 1_000_000))
        stock_micro = min(
            quantise(plan.prepositioned.get(cid, 0.0)),
            quantise(consignment.prepositioned_qty),
        )
        if shipped + stock_micro + 0.5 < demand_micro:
            shortage = demand_micro - shipped - stock_micro
            detail = "network unreachable for the class" if not cut else (
                "min cut " + ",".join(f"{u}->{v}" for u, v in cut)
            )
            add("GATE-FLOW-001", cid, consignment.origin,
                f"max flow {shipped / 1_000_000:.3f} plus forward stock "
                f"{stock_micro / 1_000_000:.3f} below demand {consignment.qty:.3f} "
                f"(short {shortage / 1_000_000:.3f}); {detail}")

        excursion_min[cid] = int(round(excursion))

    containers: Dict[str, set] = {}
    for leg in plan.legs:
        if leg.container:
            containers.setdefault(leg.container, set()).add(leg.consignment)
    for container_id, members in sorted(containers.items()):
        classes = {network.consignment(cid).temp_class for cid in members}
        if len(classes) > 1:
            for cid in sorted(members):
                add("GATE-TEMP-001", cid, container_id,
                    "mixed temperature classes: " + ", ".join(sorted(classes)))

    # Flag rules: one loop, one row per rule. `scope` decides the subjects.
    notice = event.get("notice_min")
    flag_context = {
        "freshness": thresholds.freshness_limit_min,
        "notice_zero": notice in (0, "0"),
    }
    for rule in FLAG_RULES:
        subjects = RULE_SUBJECTS[rule.scope](network)
        for subject in subjects:
            if not rule.condition(network, plan, subject, flag_context):
                continue
            add(
                rule.code,
                subject.id if subject is not None else "*",
                rule.location(network, plan, subject, flag_context),
                rule.message(network, plan, subject, flag_context),
            )

    blocked_modes = {lane.mode for lane in network.lanes if lane.blocked_until_min > 0}
    for consignment in network.consignments:
        modes = {network.lane(leg.lane).mode for leg in plan.legs_of(consignment.id)}
        backup = plan.backup_modes.get(consignment.id)
        if len(modes) == 1 and modes & blocked_modes and not (backup and backup not in blocked_modes):
            mode = sorted(modes)[0]
            add("GATE-MODE-001", consignment.id, mode,
                f"single mode dependence while {mode} has an open block")

    # --- Physical layers (SW-11) -------------------------------------
    # Metrics first, rules second. Every physical check is a row in
    # PHYSICAL_RULES applied by one loop, so a new check is data, not a branch.
    hours = max(1, network.horizon_min // 60)
    utilisation_by_station: Dict[str, int] = {}
    carriers_by_station: Dict[str, List[str]] = {}
    for leg in plan.legs:
        lane = network.lane(leg.lane)
        cargo = quantise(network.consignment(leg.consignment).qty)
        utilisation_by_station[lane.src] = utilisation_by_station.get(lane.src, 0) + cargo
        carriers_by_station.setdefault(lane.src, []).append(leg.consignment)
    for carrier_ids in carriers_by_station.values():
        carrier_ids.sort()
    station_metrics: Dict[str, Dict[str, int]] = {}
    for nid in sorted(utilisation_by_station):
        node = network.nodes.get(nid)
        if node is None:
            continue
        station_metrics[nid] = {
            "utilisation": utilisation_permille(
                utilisation_by_station[nid], quantise(node.capacity_per_hour), hours
            )
        }
    for nid, values in station_metrics.items():
        bucket = min(len(physics().delay_table) - 1, values["utilisation"] // 50)
        for cid in carriers_by_station.get(nid, ()):
            metrics[cid].setdefault("queue_utilisation", 0)
            if values["utilisation"] >= metrics[cid]["queue_utilisation"]:
                metrics[cid]["queue_utilisation"] = values["utilisation"]
                metrics[cid]["station"] = nid  # type: ignore[assignment]
                metrics[cid]["factor"] = physics().delay_table[bucket]  # type: ignore[assignment]

    # Service floor: only *deliberate* deferral counts here. A consignment that
    # the network cannot move at all is already a GATE-FLOW-001 finding, and
    # double-counting it would punish a planner for the state of the network.
    total_micro = sum(quantise(c.qty) for c in network.consignments)
    deferred_micro = sum(
        quantise(c.qty) for c in network.consignments if c.id in plan.deferred
    )
    served = served_permille(total_micro - deferred_micro, total_micro)

    scoped_metrics = {
        "consignment": metrics,
        "network": {"*": {"served": served}},
    }
    for rule in PHYSICAL_RULES:
        subject_metrics = scoped_metrics[rule.scope]
        limit = int(getattr(thresholds, rule.limit))
        for subject in sorted(subject_metrics):
            values = subject_metrics[subject]
            if rule.metric not in values:
                continue
            measured = int(values[rule.metric])
            if not COMPARATORS[rule.comparator](measured, limit):
                continue
            add(
                rule.code,
                subject,
                str(values.get("station", "route" if rule.scope == "consignment" else subject)),
                rule.template.format(value=measured, limit=limit, **values),
            )

    findings.sort(key=lambda f: (f.consignment, f.code, f.location, f.measurement))
    verdict = next(
        label for predicate, label in VERDICT_RULES if predicate(findings)
    )
    conditions = tuple(sorted({f.remedy for f in findings if f.severity == WARN}))
    return Release(
        verdict=verdict,
        findings=tuple(findings),
        conditions=conditions,
        hash=plan_hash(network, plan, event, thresholds),
        network=network.name,
        strategy=plan.strategy,
        excursion_min=excursion_min,
        thermal_dose=thermal,
        availability=available,
        served=served,
    )


def _is_block(code: str) -> bool:
    return code in {
        "GATE-TEMP-001",
        "GATE-TEMP-002",
        "GATE-TEMP-004",
        "GATE-TEMP-005",
        "GATE-SLACK-001",
        "GATE-FLOW-001",
        "GATE-HANDOFF-001",
        "GATE-DATA-001",
        "GATE-PLAN-002",
        "GATE-NODE-001",
        "GATE-DATA-002",
        "GATE-LEGAL-001",
        "GATE-NODE-002",
        "GATE-PARTY-001",
        "GATE-HANDOFF-003",
        "GATE-QUEUE-001",
        "GATE-THERM-006",
        "GATE-RELIAB-001",
        "GATE-SERVICE-001",
    }


