"""The 36-dimension state vector (BHR-RS-14).

A scenario is a network plus an event vector, and both are already structured.
This module flattens them into one fixed-length integer vector so the same row
can feed a classifier, a regression, a distance metric or a figure in a paper
without a second definition of "the features".

Design rules
------------
* One row, thirty-six columns, six groups: thermal, network, geography and time,
  institutions, event axes, weather, risk. The manifest reports the count so a
  paper can cite it and a test can fail if it drifts.
* Integers or per-mille only. A float column would make `json` round-trip and
  two-language parity arguments harder than they need to be.
* Every column is derived from data that already exists in the instance. Nothing
  here is a latent variable: if a reader cannot recompute a column from the
  scenario files, the column does not belong.
* Ordinal columns use tables, not ladders. Adding a duration class is adding a
  row to `DURATION_ORDINAL_PERMILLE`.

The time dimension
------------------
The vector is a snapshot, and a snapshot loses sequence. `temporal_stack`
returns the same columns ordered by event notice, duration and onset, which is
the smallest structure that lets a reader see "how much warning, how long, how
fast" without inventing a fifth axis. A full trajectory encoder is future work
and is recorded as such in BHR-RS-14.
"""

from __future__ import annotations

from statistics import fmean
from typing import Dict, List, Optional, Sequence, Tuple

from . import risk, weather
from .gate import Release
from .model import Network, Plan

PERMILLE = 1000
VERSION = "1.0"

# Ordinal tables: a class becomes a number once, here, and every consumer reads
# the same mapping.
DURATION_ORDINAL_PERMILLE = {"hours": 250, "days": 500, "weeks": 750, "months": 1000}
SCOPE_ORDINAL_PERMILLE = {"node": 250, "lane": 500, "region": 750, "global": 1000}
ONSET_ORDINAL_PERMILLE = {"gradual": 500, "instant": 1000}
REVERSIBILITY_ORDINAL_PERMILLE = {"recoverable": 500, "structural": 1000}
NOTICE_MINUTES = {0: 0, "hours": 240, "days": 1440}

# name, group, unit, key in the facts table.
DIMENSIONS: Tuple[Tuple[str, str, str, str], ...] = (
    ("thermal.frozen_share", "thermal", "permille", "frozen_share_permille"),
    ("thermal.chilled_share", "thermal", "permille", "chilled_share_permille"),
    ("thermal.mean_heat_gain", "thermal", "permille", "mean_heat_gain_permille"),
    ("thermal.min_quality_budget", "thermal", "minute", "min_quality_budget_min"),
    ("thermal.zero_allowance_share", "thermal", "permille", "zero_allowance_share_permille"),
    ("thermal.load", "thermal", "permille", "thermal_load_permille"),
    ("network.node_count", "network", "count", "node_count"),
    ("network.lane_count", "network", "count", "lane_count"),
    ("network.controlled_share", "network", "permille", "controlled_share_permille"),
    ("network.monitored_share", "network", "permille", "monitored_share_permille"),
    ("geo.region_count", "geography", "count", "region_count"),
    ("geo.cross_border_share", "geography", "permille", "cross_border_share_permille"),
    ("geo.mean_travel_min", "geography", "minute", "mean_travel_min"),
    ("time.horizon_min", "geography", "minute", "horizon_min"),
    ("inst.tariff_shock", "institutions", "permille", "tariff_shock_permille"),
    ("inst.export_control", "institutions", "permille", "export_control_permille"),
    ("inst.labour_action", "institutions", "permille", "labour_action_permille"),
    ("inst.financial_default", "institutions", "permille", "financial_default_permille"),
    ("inst.cyber_intrusion", "institutions", "permille", "cyber_intrusion_permille"),
    ("inst.capacity_loss", "institutions", "permille", "capacity_loss_permille"),
    ("inst.lead_time_inflation", "institutions", "permille", "lead_time_inflation_permille"),
    ("inst.blocked_lane_share", "institutions", "permille", "blocked_share_permille"),
    ("event.notice_min", "event", "minute", "notice_min"),
    ("event.duration_ordinal", "event", "permille", "duration_ordinal_permille"),
    ("event.scope_ordinal", "event", "permille", "scope_ordinal_permille"),
    ("event.reversibility", "event", "permille", "reversibility_permille"),
    ("event.onset_ordinal", "event", "permille", "onset_ordinal_permille"),
    ("weather.severity", "weather", "0.1degC", "severity_c_tenths"),
    ("weather.band_gap_max", "weather", "0.1degC", "band_gap_max_tenths"),
    ("weather.multiplier_max", "weather", "permille", "multiplier_max_permille"),
    ("weather.humidity_max", "weather", "permille", "humidity_max_permille"),
    ("weather.solar_max", "weather", "permille", "solar_max_permille"),
    ("weather.storm_max", "weather", "permille", "storm_max_permille"),
    ("risk.p_exceedance", "risk", "permille", "exceedance_permille"),
    ("risk.expected_dose", "risk", "permille", "expected_dose_permille"),
    ("risk.value_at_risk", "risk", "usd", "value_at_risk_usd"),
)

COLUMNS = tuple(row[0] for row in DIMENSIONS)


def _share(part: int, whole: int) -> int:
    return 0 if whole <= 0 else (part * PERMILLE) // whole


def _flag(value: object) -> int:
    return PERMILLE if value else 0


def _dig(mapping: dict, *path: str, default: object = 0) -> object:
    """Read a nested key with a default, so a partial event never raises."""
    node: object = mapping
    for key in path:
        if not isinstance(node, dict) or key not in node:
            return default
        node = node[key]
    return node


def _facts(
    network: Network,
    event: dict,
    report: weather.WeatherReport,
    scored: Optional[dict] = None,
) -> Dict[str, int]:
    """Every column of the vector, computed once from real fields."""
    consignments = network.consignments
    lanes = network.lanes
    total = len(consignments)
    lane_total = len(lanes)
    classes = tuple(consignment.temp_class for consignment in consignments)
    budgets = tuple(max(1, consignment.quality_budget_min) for consignment in consignments)
    load = (
        int(round(fmean(c.heat_gain_permille * PERMILLE / budget for c, budget in zip(consignments, budgets))))
        if total
        else 0
    )
    magnitude = event.get("magnitude", {})
    peak_region = max(report.regions, key=lambda region: region.peak_c_tenths)
    return {
        "frozen_share_permille": _share(classes.count("frozen"), total),
        "chilled_share_permille": _share(classes.count("chilled"), total),
        "mean_heat_gain_permille": (
            int(round(fmean(consignment.heat_gain_permille for consignment in consignments)))
            if total
            else 0
        ),
        "min_quality_budget_min": min(budgets) if budgets else 0,
        "zero_allowance_share_permille": _share(
            sum(1 for c in consignments if c.excursion_allowance_min == 0), total
        ),
        "thermal_load_permille": load,
        "node_count": len(network.nodes),
        "lane_count": lane_total,
        "controlled_share_permille": _share(
            sum(1 for lane in lanes if lane.controlled), lane_total
        ),
        "monitored_share_permille": _share(
            sum(1 for lane in lanes if lane.monitored), lane_total
        ),
        "region_count": len({node.region for node in network.nodes.values()}),
        "cross_border_share_permille": _share(
            sum(1 for lane in lanes if lane.cross_border), lane_total
        ),
        "mean_travel_min": int(round(fmean(lane.travel_min for lane in lanes))) if lanes else 0,
        "horizon_min": network.horizon_min,
        "tariff_shock_permille": int(
            round(float(_dig(event, "catalysts", "geoeconomic", "tariff_shock_pct")) * PERMILLE)
        ),
        "export_control_permille": _flag(
            _dig(event, "catalysts", "geoeconomic", "export_control")
        ),
        "labour_action_permille": _flag(_dig(event, "catalysts", "labour", "action")),
        "financial_default_permille": _flag(_dig(event, "catalysts", "financial", "default")),
        "cyber_intrusion_permille": _flag(_dig(event, "catalysts", "cyber", "intrusion")),
        "capacity_loss_permille": int(
            round(float(magnitude.get("capacity_loss", 0.0)) * PERMILLE)
        ),
        "lead_time_inflation_permille": int(
            round(float(magnitude.get("lead_time_inflation", 0.0)) * PERMILLE)
        ),
        "blocked_share_permille": _share(
            sum(1 for lane in lanes if lane.blocked_until_min > 0), lane_total
        ),
        "notice_min": NOTICE_MINUTES.get(event.get("notice_min"), 0),
        "duration_ordinal_permille": DURATION_ORDINAL_PERMILLE.get(event.get("duration"), 0),
        "scope_ordinal_permille": SCOPE_ORDINAL_PERMILLE.get(event.get("scope"), 0),
        "reversibility_permille": REVERSIBILITY_ORDINAL_PERMILLE.get(
            event.get("reversibility"), 0
        ),
        "onset_ordinal_permille": ONSET_ORDINAL_PERMILLE.get(event.get("onset_rate"), 0),
        "severity_c_tenths": report.severity_c_tenths,
        "band_gap_max_tenths": max(report.degrees_above_band.values(), default=0),
        "multiplier_max_permille": max(report.multiplier_permille.values(), default=PERMILLE),
        "humidity_max_permille": peak_region.humidity_permille,
        "solar_max_permille": max(region.solar_permille for region in report.regions),
        "storm_max_permille": max(region.storm_permille for region in report.regions),
        "exceedance_permille": int(round((scored or {}).get("p_any_exceedance", 0.0) * PERMILLE)),
        "expected_dose_permille": int((scored or {}).get("expected_dose_permille", 0)),
        "value_at_risk_usd": int(round((scored or {}).get("value_at_risk_usd", 0.0))),
    }


def vector(
    network: Network,
    event: dict,
    report: Optional[weather.WeatherReport] = None,
    release: Optional[Release] = None,
    plan: Optional[Plan] = None,
) -> Tuple[int, ...]:
    """One row of thirty-six integers. Pass `release` and `plan` to score risk.

    Without a gate run the three risk columns are zero rather than guessed: an
    unmeasured probability is not a probability.
    """
    report = report if report is not None else weather.assess(event)
    scored = (
        risk.portfolio(network, plan, release, report)
        if plan is not None and release is not None
        else None
    )
    facts = _facts(network, event, report, scored)
    return tuple(int(facts[key]) for _, _, _, key in DIMENSIONS)


def as_dict(row: Tuple[int, ...]) -> Dict[str, int]:
    """Column name to value, for tables and figures."""
    if len(row) != len(DIMENSIONS):
        raise ValueError(f"expected {len(DIMENSIONS)} columns, got {len(row)}")
    return {name: int(value) for name, value in zip(COLUMNS, row)}


def manifest() -> Dict[str, object]:
    """The citable description of the vector: count, version, columns."""
    return {
        "version": VERSION,
        "dimension_count": len(DIMENSIONS),
        "groups": sorted({group for _, group, _, _ in DIMENSIONS}),
        "columns": [
            {"name": name, "group": group, "unit": unit}
            for name, group, unit, _ in DIMENSIONS
        ],
    }


def _order_key(event: dict) -> Tuple[int, int, int]:
    return (
        NOTICE_MINUTES.get(event.get("notice_min"), 0),
        DURATION_ORDINAL_PERMILLE.get(event.get("duration"), 0),
        ONSET_ORDINAL_PERMILLE.get(event.get("onset_rate"), 0),
    )


def temporal_stack(
    rows: Sequence[Tuple[dict, Tuple[int, ...]]],
) -> Tuple[Tuple[dict, Tuple[int, ...]], ...]:
    """Order (event, vector) pairs by notice, duration, onset.

    A snapshot loses sequence. This is the smallest ordering that restores it:
    how much warning, how long, how fast. It is ordering, not a trajectory
    encoder, and BHR-RS-14 records the difference.
    """
    return tuple(sorted(rows, key=lambda row: _order_key(row[0])))


