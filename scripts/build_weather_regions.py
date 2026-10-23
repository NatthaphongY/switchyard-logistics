"""Build the region profile table from open reanalysis (BHR-RS-13).

Why this script exists
----------------------
The first version of the ambient layer carried three invented profiles. The
mechanism was measured and the numbers were honest, but the geography was not:
a reviewer could not check where 18.5 C came from. This script replaces the
invented table with a frozen snapshot of a public reanalysis, and it keeps the
snapshot in the repository so the run stays reproducible offline.

Source
------
Open-Meteo archive API, which serves ERA5 reanalysis (Copernicus Climate Change
Service). No key, no account, no cost. Attribution is stored in the output file
because the licence requires it (CC BY 4.0).

What is frozen
--------------
Thirty July normals, 1991 to 2020, one daily aggregate series per site. The
derivation is integer arithmetic from start to finish, so the profiles the
simulation consumes carry no float.

    base_c_tenths       mean of the daily mean temperature, tenths of a degree
    swing_c_tenths      half the mean diurnal range, tenths of a degree
    humidity_permille   mean daily relative humidity, per-mille
    solar_permille      mean daily shortwave energy against a 30 MJ/m2 reference
    storm_permille      share of days with at least 1 mm of precipitation

Re-running
----------
    py -3.13 -X utf8 research/scripts/build_weather_regions.py --dry-run
    py -3.13 -X utf8 research/scripts/build_weather_regions.py

The run is not bit-identical across days: `retrieved_utc` records when the
snapshot was taken, exactly as `elapsed_s` does in the evidence files. Every
other field is a function of the fetched series alone.
"""

from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Sequence

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config"
REGIONS_PATH = CONFIG / "weather_regions.json"
WEATHER_PATH = CONFIG / "weather.json"

ENDPOINT = "https://archive-api.open-meteo.com/v1/archive"
MONTH = 7
FIRST_YEAR = 1991
LAST_YEAR = 2020
DAILY_FIELDS = (
    "temperature_2m_max",
    "temperature_2m_min",
    "temperature_2m_mean",
    "relative_humidity_2m_mean",
    "shortwave_radiation_sum",
    "precipitation_sum",
)
WET_DAY_MILLI_MM = 1000            # 1.0 mm expressed in thousandths of a millimetre
SOLAR_REFERENCE_MILLI_MJ = 30000   # 30 MJ/m2 per day, in thousandths
PERMILLE = 1000
ATTEMPTS = 3

# Three real sites, one per climate class the scenario generator can emit. The
# keys are the region identifiers the network already uses; the labels say what
# the climate is, and the site says where the numbers were measured.
SITES: Sequence[dict] = (
    {
        "key": "R0",
        "label": "temperate maritime",
        "site": "Frankfurt am Main, DE",
        "latitude": 50.1109,
        "longitude": 8.6821,
    },
    {
        "key": "R1",
        "label": "humid subtropical",
        "site": "Guangzhou, CN",
        "latitude": 23.1291,
        "longitude": 113.2644,
    },
    {
        "key": "R2",
        "label": "continental interior",
        "site": "Ulaanbaatar, MN",
        "latitude": 47.8864,
        "longitude": 106.9057,
    },
)


def _ratio(num: int, den: int) -> int:
    """Half-up integer division for non-negative values. No float anywhere."""
    return (2 * num + den) // (2 * den)


def _request(site: dict) -> dict:
    query = {
        "latitude": site["latitude"],
        "longitude": site["longitude"],
        "start_date": f"{FIRST_YEAR}-01-01",
        "end_date": f"{LAST_YEAR}-12-31",
        "daily": ",".join(DAILY_FIELDS),
        "timezone": "UTC",
    }
    url = ENDPOINT + "?" + urllib.parse.urlencode(query)
    last: Exception | None = None
    for attempt in range(1, ATTEMPTS + 1):
        try:
            with urllib.request.urlopen(url, timeout=90) as response:
                return json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as exc:
            last = exc
            if attempt < ATTEMPTS:
                time.sleep(attempt * 2)


def _thousandths(value: float) -> int:
    """One float crossing, at the boundary of the data, never inside the model."""
    return int(round(value * PERMILLE))


def _july_series(payload: dict) -> Dict[str, List[int]]:
    daily = payload["daily"]
    days = daily["time"]
    keep = [i for i, stamp in enumerate(days) if int(stamp[5:7]) == MONTH]
    if not keep:
        raise RuntimeError("no July rows in the archive response")
    series: Dict[str, List[int]] = {}
    for field in DAILY_FIELDS:
        raw = daily[field]
        values = []
        for index in keep:
            item = raw[index]
            if item is None:
                continue
            values.append(_thousandths(item))
        if not values:
            raise RuntimeError(f"empty series for {field}")
        series[field] = values
    return series


def _mean(values: Sequence[int]) -> int:
    return _ratio(sum(values), len(values))


def profile_from_series(series: Dict[str, List[int]], site: dict) -> dict:
    """Derive one region profile from one site's July series. Pure integers."""
    mean_c = _mean(series["temperature_2m_mean"])
    mean_max = _mean(series["temperature_2m_max"])
    mean_min = _mean(series["temperature_2m_min"])
    humidity = _mean(series["relative_humidity_2m_mean"])
    solar = _mean(series["shortwave_radiation_sum"])
    wet = sum(1 for value in series["precipitation_sum"] if value >= WET_DAY_MILLI_MM)
    solar_permille = min(PERMILLE, _ratio(solar * PERMILLE, SOLAR_REFERENCE_MILLI_MJ))
    return {
        "key": site["key"],
        "label": site["label"],
        "base_c_tenths": _ratio(mean_c, 100),
        "swing_c_tenths": _ratio(mean_max - mean_min, 200),
        "humidity_permille": _ratio(humidity, 100),
        "solar_permille": solar_permille,
        "storm_permille": _ratio(wet * PERMILLE, len(series["precipitation_sum"])),
        "observed": {
            "mean_c_thousandths": mean_c,
            "mean_daily_max_c_thousandths": mean_max,
            "mean_daily_min_c_thousandths": mean_min,
            "mean_humidity_thousandths": humidity,
            "mean_shortwave_mj_m2_thousandths": solar,
            "days": len(series["precipitation_sum"]),
            "wet_days": wet,
        },
        "site": {
            "name": site["site"],
            "latitude": site["latitude"],
            "longitude": site["longitude"],
        },
    }


def synthetic_profile() -> dict:
    """The invented table the earlier evidence used, kept for exact replay.

    Reading it from the region file first means re-running this script never
    loses the numbers that the published evidence quotes.
    """
    if REGIONS_PATH.is_file():
        existing = json.loads(REGIONS_PATH.read_text(encoding="utf-8"))
        block = existing.get("profiles", {}).get("synthetic")
        if block and block.get("regions"):
            return block["regions"]
    inline = json.loads(WEATHER_PATH.read_text(encoding="utf-8"))["regions"]
    return {
        key: {
            "label": value["label"],
            "base_c_tenths": value["base_c_tenths"],
            "swing_c_tenths": value["swing_c_tenths"],
            "humidity_permille": value["humidity_permille"],
            "solar_permille": value["solar_permille"],
            "storm_permille": value["storm_permille"],
        }
        for key, value in sorted(inline.items())
    }


    raise RuntimeError(f"archive request failed for {site['site']}: {last}")



def build() -> dict:
    regions = {}
    sites = {}
    for site in SITES:
        payload = _request(site)
        series = _july_series(payload)
        profile = profile_from_series(series, site)
        regions[site["key"]] = {
            key: value for key, value in profile.items() if key not in {"key", "site"}
        }
        sites[site["key"]] = profile["site"]
        observed = profile["observed"]
        print(
            f"{site['key']} {site['site']}: base {profile['base_c_tenths'] / 10:.1f} C, "
            f"swing {profile['swing_c_tenths'] / 10:.1f} C, "
            f"humidity {profile['humidity_permille']}, solar {profile['solar_permille']}, "
            f"storm {profile['storm_permille']} "
            f"({observed['wet_days']}/{observed['days']} wet days)"
        )
    return {
        "_comment": (
            "Region profiles for the ambient layer (BHR-RS-13). Integers only. "
            "'measured' is a frozen July climatology from open reanalysis; "
            "'synthetic' is the invented table kept so older evidence replays. "
            "Rebuild with research/scripts/build_weather_regions.py."
        ),
        "version": "2.0",
        "active": "measured",
        "profiles": {
            "measured": {
                "source": {
                    "kind": "reanalysis climatology",
                    "product": "ERA5 reanalysis via the Open-Meteo archive API",
                    "endpoint": ENDPOINT,
                    "month": MONTH,
                    "period": f"{FIRST_YEAR}-{LAST_YEAR}",
                    "retrieved_utc": datetime.now(timezone.utc).strftime(
                        "%Y-%m-%dT%H:%M:%SZ"
                    ),
                    "cost": "free, keyless, no account",
                    "licence": (
                        "Open-Meteo data CC BY 4.0; ERA5 (C) Copernicus Climate "
                        "Change Service, ECMWF"
                    ),
                    "attribution": (
                        "Weather data by Open-Meteo.com (CC BY 4.0), derived from "
                        "ERA5 reanalysis (Copernicus Climate Change Service)"
                    ),
                    "derivation": {
                        "base_c_tenths": "mean daily mean temperature, tenths of a degree",
                        "swing_c_tenths": "half the mean diurnal range, tenths of a degree",
                        "humidity_permille": "mean daily relative humidity, per-mille",
                        "solar_permille": (
                            "mean daily shortwave energy against a 30 MJ/m2 reference, "
                            "capped at 1000"
                        ),
                        "storm_permille": (
                            "share of July days with at least 1 mm of precipitation, "
                            "per-mille"
                        ),
                        "arithmetic": "integer only; one float at the data boundary",
                    },
                    "sites": sites,
                },
                "regions": regions,
            },
            "synthetic": {
                "source": {
                    "kind": "invented",
                    "note": (
                        "Placeholder table used before the ingest was wired. Retained "
                        "only so the earlier evidence files replay exactly."
                    ),
                },
                "regions": synthetic_profile(),
            },
        },
    }



def main() -> int:
    parser = argparse.ArgumentParser(description="Build the region profile table")
    parser.add_argument("--dry-run", action="store_true", help="print, do not write")
    args = parser.parse_args()

    document = build()
    if args.dry_run:
        print(json.dumps(document["profiles"]["measured"]["regions"], indent=2))
        return 0
    REGIONS_PATH.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"\nwritten: {REGIONS_PATH.relative_to(ROOT.parent)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
