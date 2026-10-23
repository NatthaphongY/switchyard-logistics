"""Weather layer (SW-11): ambient conditions as integer data.

Why the layer exists
--------------------
Before it, `heat_gain_permille` was a constant drawn per temperature class. The
thermal gate was therefore blind to ambient state: a frozen consignment sitting
in 38 C scored the same as one sitting in 12 C. The gate was correct and
incomplete, which is the expensive kind of correct.

What it is
----------
A deterministic projection of the six event axes onto regional ambient state:
peak and mean dry-bulb temperature, humidity, solar load, storm overlap. All
values are tenths of a degree or per-mille, so nothing here is a float and the
instances exported to the Rust core keep replaying byte-identically.

Where the numbers come from
---------------------------
`config/weather_regions.json` carries two profile sets. `measured` is a frozen
July climatology (1991 to 2020) derived from ERA5 reanalysis served by the
Open-Meteo archive API: free, keyless, and attributed inside the file because
the licence asks for it. `synthetic` is the invented table the earlier evidence
used, kept so those numbers replay exactly. `active` names the default and
`profile=` selects the other one without touching a formula.

This is still not a live forecast ingest: the table is a frozen snapshot, and a
live forecast is the same seam with a fresher snapshot. The calibration rule is
unchanged -- replace the table, keep every formula, re-export the instances,
re-run parity.

Advisory only
-------------
`findings` reports plan-level weather weaknesses. They are advisory: they do not
enter `verdict`, `unsafe_control_actions` or `blocks`, because the Rust core
computes exactly those three counters and parity must stay exact. Promoting an
advisory to blocking means implementing it on both sides in the same commit.
Weather changes decisions today through the heat gain it supplies.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, replace
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .model import Network, Plan

CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "weather.json"
REGIONS_PATH = Path(__file__).resolve().parents[2] / "config" / "weather_regions.json"
PROFILE_ENV = "SW_WEATHER_PROFILE"
PERMILLE = 1000


@lru_cache(maxsize=1)
def config() -> dict:
    """Load the formula table once. Data, not code (README section 3, item 7)."""
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def profiles() -> dict:
    """Load the region profile table once. A frozen snapshot, not a live feed."""
    return json.loads(REGIONS_PATH.read_text(encoding="utf-8"))


def profile_names() -> Tuple[str, ...]:
    return tuple(sorted(profiles()["profiles"]))


def active_profile(profile: Optional[str] = None) -> str:
    """Resolve which profile to use: explicit argument, then environment, then file.

    The environment override exists so a reviewer can rebuild an older result
    (`SW_WEATHER_PROFILE=synthetic`) without editing a committed file.
    """
    chosen = profile or os.environ.get(PROFILE_ENV) or profiles()["active"]
    if chosen not in profiles()["profiles"]:
        raise KeyError(f"unknown weather profile {chosen!r}; have {profile_names()}")
    return chosen


def regions(profile: Optional[str] = None) -> Dict[str, dict]:
    """Region profiles for the chosen set, keyed by the network's region id."""
    return profiles()["profiles"][active_profile(profile)]["regions"]


def source(profile: Optional[str] = None) -> dict:
    """Provenance for the chosen profile, so a report can cite it."""
    return profiles()["profiles"][active_profile(profile)]["source"]



@dataclass(frozen=True)
class RegionWeather:
    """Ambient state for one region under one event."""

    key: str
    label: str
    peak_c_tenths: int
    mean_c_tenths: int
    humidity_permille: int
    solar_permille: int
    storm_permille: int

    def as_dict(self) -> dict:
        return {
            "region": self.key,
            "label": self.label,
            "peak_c": self.peak_c_tenths / 10.0,
            "mean_c": self.mean_c_tenths / 10.0,
            "humidity_permille": self.humidity_permille,
            "solar_permille": self.solar_permille,
            "storm_permille": self.storm_permille,
        }


@dataclass(frozen=True)
class WeatherReport:
    """Ambient state plus the heat multipliers it implies per temperature class."""

    version: str
    severity_c_tenths: int
    regions: Tuple[RegionWeather, ...]
    band_top_c_tenths: Dict[str, int]
    degrees_above_band: Dict[str, int]
    multiplier_permille: Dict[str, int]

    @property
    def affected_regions(self) -> Tuple[str, ...]:
        return tuple(region.key for region in self.regions)

    def region(self, key: str) -> RegionWeather:
        return next(region for region in self.regions if region.key == key)

    def as_dict(self) -> dict:
        return {
            "version": self.version,
            "severity_c": self.severity_c_tenths / 10.0,
            "affected_regions": list(self.affected_regions),
            "regions": [region.as_dict() for region in self.regions],
            "band_top_c": {
                key: value / 10.0 for key, value in self.band_top_c_tenths.items()
            },
            "degrees_above_band": {
                key: value / 10.0 for key, value in self.degrees_above_band.items()
            },
            "multiplier": {
                key: value / PERMILLE for key, value in self.multiplier_permille.items()
            },
        }


def severity_c_tenths(event: dict, intensity: float = 1.0, scale: float = 1.0) -> int:
    """Event axes to a temperature anomaly, in tenths of a degree.

    Duration sets the order of magnitude, onset decides how much of it lands, and
    the capacity-loss axis stands in for magnitude until a forecast supplies the
    real anomaly. The result is clamped by the configured ceiling so one axis
    cannot dominate.
    """
    cfg = config()
    duration_pm = cfg["duration_severity_tenths"][event["duration"]]
    onset_pm = cfg["onset_severity_permille"][event["onset_rate"]]
    magnitude_pm = int(
        round(PERMILLE * event["magnitude"]["capacity_loss"] * intensity * scale)
    )
    raw = (duration_pm * onset_pm * magnitude_pm) // cfg["severity_divisor"]
    return max(0, min(cfg["severity_ceiling_c_tenths"], raw))


def _region_state(key: str, profile: dict, severity: int) -> RegionWeather:
    solar_bonus = (severity * profile["solar_permille"]) // 5000
    peak = profile["base_c_tenths"] + profile["swing_c_tenths"] + severity + solar_bonus
    return RegionWeather(
        key=key,
        label=profile["label"],
        peak_c_tenths=peak,
        mean_c_tenths=profile["base_c_tenths"] + severity // 2,
        humidity_permille=min(PERMILLE, profile["humidity_permille"] + severity * 8),
        solar_permille=profile["solar_permille"],
        storm_permille=min(
            PERMILLE,
            (profile["storm_permille"] * (PERMILLE + severity * 12)) // PERMILLE,
        ),
    )


def assess(
    event: dict,
    seed: int = 0,
    intensity: float = 1.0,
    scale: float = 1.0,
    profile: Optional[str] = None,
) -> WeatherReport:
    """Build the weather report for one event vector. Pure and reproducible.

    `scale` exists for the parametric ensemble in SW-11: it perturbs the
    anomaly without touching the network, so members differ only in weather.
    `profile` selects the region table; its default comes from the data file,
    so a reviewer can replay an older run without editing a committed file.
    """
    cfg = config()
    table = regions(profile)
    severity = severity_c_tenths(event, intensity, scale)
    keys = sorted(table)
    count = min(len(keys), cfg["scope_regions"][event["scope"]])
    offset = seed % len(keys)
    chosen = [keys[(offset + step) % len(keys)] for step in range(count)]
    states = tuple(_region_state(key, table[key], severity) for key in chosen)
    peak = max(state.peak_c_tenths for state in states)
    band_top = {key: int(value) for key, value in cfg["bands_c_tenths"].items()}
    degrees = {key: max(0, peak - band_top[key]) for key in band_top}
    floor = cfg["multiplier_floor_permille"]
    ceiling = cfg["multiplier_ceiling_permille"]
    sensitivity = cfg["class_sensitivity_permille"]
    multiplier = {
        key: min(ceiling, max(floor, PERMILLE + (degrees[key] * sensitivity[key]) // PERMILLE))
        for key in band_top
    }
    return WeatherReport(
        version=str(cfg["version"]),
        severity_c_tenths=severity,
        regions=states,
        band_top_c_tenths=band_top,
        degrees_above_band=degrees,
        multiplier_permille=multiplier,
    )


def apply(network: Network, report: WeatherReport) -> Network:
    """Re-price every consignment's heat gain under the forecast.

    The gate and the planners are untouched: they already consume
    `heat_gain_permille`, so a warmer forecast raises thermal dose through the
    path that was always there. That is why the Rust core needs no change to keep
    parity -- the exported instance simply carries the new integer.
    """
    ceiling = config()["heat_ceiling_permille"]
    consignments = tuple(
        replace(
            consignment,
            heat_gain_permille=min(
                ceiling,
                (
                    consignment.heat_gain_permille
                    * report.multiplier_permille[consignment.temp_class]
                )
                // PERMILLE,
            ),
        )
        for consignment in network.consignments
    )
    return replace(network, consignments=consignments)


def findings(network: Network, plan: Plan, report: WeatherReport) -> List[dict]:
    """Advisory findings: weather weaknesses a reviewer should see.

    Three row kinds, each a predicate over real plan fields. No branch decides
    which row applies; the rows are data and every row is tested.
    """
    cfg = config()["advisory"]
    protected = frozenset(plan.thermal_protection)
    backed_up = frozenset(plan.backup_modes)
    rows: List[dict] = []
    for consignment in network.consignments:
        cid = consignment.id
        multiplier = report.multiplier_permille[consignment.temp_class]
        gap = report.degrees_above_band[consignment.temp_class]
        rows.append(
            {
                "code": "WX-ADV-001",
                "consignment": cid,
                "location": consignment.origin,
                "fires": multiplier >= cfg["multiplier_permille"] and cid not in protected,
                "measurement": (
                    f"heat gain x{multiplier / PERMILLE:.2f} at {gap / 10.0:.1f} C above "
                    f"the {consignment.temp_class} band, no active protection booked"
                ),
            }
        )
        rows.append(
            {
                "code": "WX-ADV-003",
                "consignment": cid,
                "location": consignment.origin,
                "fires": consignment.excursion_allowance_min == 0
                and gap >= cfg["band_gap_c_tenths"],
                "measurement": (
                    f"forecast {gap / 10.0:.1f} C above the {consignment.temp_class} band "
                    "with zero excursion allowance"
                ),
            }
        )
        for leg in plan.legs_of(cid):
            lane = network.lane(leg.lane)
            region = network.nodes[lane.src].region
            storm = (
                report.region(region).storm_permille
                if region in report.affected_regions
                else 0
            )
            rows.append(
                {
                    "code": "WX-ADV-002",
                    "consignment": cid,
                    "location": lane.id,
                    "fires": lane.controlled
                    and storm >= cfg["storm_permille"]
                    and cid not in backed_up,
                    "measurement": (
                        f"storm overlap {storm} per-mille on controlled lane {lane.id} "
                        "with no backup mode"
                    ),
                }
            )
    return [
        {
            "code": row["code"],
            "severity": "warn",
            "consignment": row["consignment"],
            "location": row["location"],
            "measurement": row["measurement"],
        }
        for row in rows
        if row["fires"]
    ]


