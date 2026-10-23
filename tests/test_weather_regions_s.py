# -*- coding: utf-8 -*-
"""Gate: the region table behind the ambient layer (SW-11, 2026-10-23).

Why this gate exists
--------------------
The first ambient layer used three invented climates. The mechanism was measured
properly and the numbers were honest, but a reviewer could not check where
18.5 C came from, which is the difference between an experiment and an
assertion. The owner asked for free, checkable weather data, so the table is now
a frozen July climatology from open reanalysis, with the invented table kept as
`synthetic` so the evidence published before the swap still replays.

What the gate pins
------------------
1. The data file is integers only, ASCII, and carries its own provenance:
   product, endpoint, period, retrieval time, licence and attribution.
2. `weather.py` reads region profiles from exactly one place. A second copy in
   `weather.json` would drift silently, so its absence is asserted.
3. The derivation from a daily series is integer arithmetic and is tested on a
   fabricated series where the expected answer is computed by hand.
4. The measured table is actually different from the invented one, so a future
   edit cannot quietly restore the placeholder.
5. The artefact renders the provenance, including the invented-table warning.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from switchyard import rng, scenarios, weather  # noqa: E402

REGIONS_PATH = ROOT / "config" / "weather_regions.json"
FORMULAS_PATH = ROOT / "config" / "weather.json"
BUILDER_PATH = ROOT / "scripts" / "build_weather_regions.py"

REGION_FIELDS = ("base_c_tenths", "swing_c_tenths", "humidity_permille",
                 "solar_permille", "storm_permille")


def _data() -> dict:
    return json.loads(REGIONS_PATH.read_text(encoding="utf-8"))



# ---------------------------------------------------------------------------
# the data file
# ---------------------------------------------------------------------------

def test_region_file_declares_profiles_and_an_active_default():
    data = _data()
    assert set(data["profiles"]) == {"measured", "synthetic"}
    assert data["active"] in data["profiles"], "active must name an existing profile"
    for name, block in data["profiles"].items():
        assert block["regions"], name
        assert block["source"], f"{name} carries no provenance"


def test_measured_provenance_is_citable():
    """A climatology without its period, licence and retrieval date is unusable."""
    source = _data()["profiles"]["measured"]["source"]
    for key in ("product", "endpoint", "month", "period", "retrieved_utc",
                "licence", "attribution", "derivation", "sites"):
        assert source.get(key), f"measured source is missing {key}"
    assert "open-meteo" in source["endpoint"].lower(), "the ingest must stay keyless"
    assert "CC BY" in source["licence"], "the licence requires attribution"
    assert "Open-Meteo" in source["attribution"]
    assert source["month"] == 7 and source["period"] == "1991-2020"
    regions = _data()["profiles"]["measured"]["regions"]
    assert len(source["sites"]) == len(regions) == 3


def test_region_values_are_integers_in_plausible_ranges():
    for name, block in _data()["profiles"].items():
        for key, profile in block["regions"].items():
            for field in REGION_FIELDS:
                value = profile[field]
                assert isinstance(value, int) and not isinstance(value, bool), (
                    f"{name}.{key}.{field} must be an int, got {type(value).__name__}"
                )
            assert -500 <= profile["base_c_tenths"] <= 500, (name, key)
            assert 0 <= profile["swing_c_tenths"] <= 250, (name, key)
            assert 0 <= profile["humidity_permille"] <= 1000, (name, key)
            assert 0 <= profile["solar_permille"] <= 1000, (name, key)
            assert 0 <= profile["storm_permille"] <= 1000, (name, key)


def test_measured_table_replaced_the_placeholder():
    """If these ever match, the placeholder came back and the ingest is dead."""
    measured = _data()["profiles"]["measured"]["regions"]
    synthetic = _data()["profiles"]["synthetic"]["regions"]
    assert set(measured) == set(synthetic) == {"R0", "R1", "R2"}
    differing = [
        (key, field)
        for key in measured
        for field in REGION_FIELDS
        if measured[key][field] != synthetic[key][field]
    ]
    assert len(differing) >= 10, (
        f"measured table is suspiciously close to the placeholder: {differing}"
    )


def test_measured_regions_are_cool_to_hot_in_the_expected_order():
    """July normals: the subtropical site is the hottest and the wettest."""
    measured = _data()["profiles"]["measured"]["regions"]
    hottest = max(measured, key=lambda key: measured[key]["base_c_tenths"])
    assert hottest == "R1", "R1 is the humid subtropical site (Guangzhou)"
    assert measured["R1"]["humidity_permille"] > measured["R0"]["humidity_permille"]
    assert measured["R1"]["storm_permille"] > measured["R0"]["storm_permille"]


# ---------------------------------------------------------------------------
# one source of truth
# ---------------------------------------------------------------------------

def test_region_profiles_have_exactly_one_source():
    """`weather.json` holds formulas; the region table lives in its own file."""
    formulas = json.loads(FORMULAS_PATH.read_text(encoding="utf-8"))
    assert "regions" not in formulas, "duplicate region table in weather.json"
    assert weather.regions() == _data()["profiles"]["measured"]["regions"]


def test_profile_selection_is_argument_then_environment_then_file(monkeypatch):
    assert weather.active_profile() == _data()["active"]
    assert weather.active_profile("synthetic") == "synthetic"
    monkeypatch.setenv(weather.PROFILE_ENV, "synthetic")
    assert weather.active_profile() == "synthetic", "environment override is the replay path"
    assert weather.active_profile("measured") == "measured", "explicit argument wins"
    monkeypatch.setenv(weather.PROFILE_ENV, "not-a-profile")
    with pytest.raises(KeyError):
        weather.active_profile()


def test_synthetic_profile_replays_the_published_weather_run():
    """The earlier evidence quotes multipliers from that table, so it stays."""
    event = scenarios.sample_event(rng.StreamRandom(11))
    measured = weather.assess(event, seed=11, profile="measured")
    synthetic = weather.assess(event, seed=11, profile="synthetic")
    assert measured.multiplier_permille != synthetic.multiplier_permille
    assert [region.key for region in synthetic.regions] == [
        region.key for region in measured.regions
    ]


# ---------------------------------------------------------------------------
# the derivation
# ---------------------------------------------------------------------------

def test_derivation_is_integer_arithmetic_with_a_hand_computed_expectation():
    """Four July days, values chosen so every step can be checked by hand.

    mean 25.00 C -> 250 tenths; half the diurnal range (30.00 - 20.00) / 2 = 50
    tenths; humidity 80 % -> 800 per-mille; 15 MJ/m2 against 30 -> 500
    per-mille; 2 wet days of 4 -> 500 per-mille.
    """
    builder = _builder()
    series = {
        "temperature_2m_mean": [25000, 25000, 25000, 25000],
        "temperature_2m_max": [30000, 30000, 30000, 30000],
        "temperature_2m_min": [20000, 20000, 20000, 20000],
        "relative_humidity_2m_mean": [80000, 80000, 80000, 80000],
        "shortwave_radiation_sum": [15000, 15000, 15000, 15000],
        "precipitation_sum": [0, 1000, 0, 5000],
    }
    site = {"key": "R9", "label": "test", "site": "Nowhere",
            "latitude": 0.0, "longitude": 0.0}
    profile = builder.profile_from_series(series, site)
    assert profile["base_c_tenths"] == 250
    assert profile["swing_c_tenths"] == 50
    assert profile["humidity_permille"] == 800
    assert profile["solar_permille"] == 500
    assert profile["storm_permille"] == 500
    assert profile["observed"]["wet_days"] == 2


def test_derivation_caps_solar_and_keeps_integers():
    builder = _builder()
    series = {
        "temperature_2m_mean": [10000],
        "temperature_2m_max": [12000],
        "temperature_2m_min": [8000],
        "relative_humidity_2m_mean": [50000],
        "shortwave_radiation_sum": [99000],      # far past the reference
        "precipitation_sum": [0],
    }
    site = {"key": "R9", "label": "test", "site": "Nowhere",
            "latitude": 0.0, "longitude": 0.0}
    profile = builder.profile_from_series(series, site)
    assert profile["solar_permille"] == 1000
    assert all(
        isinstance(profile[field], int) for field in REGION_FIELDS
    ), "no float may enter the profile"


# ---------------------------------------------------------------------------
# the artefact
# ---------------------------------------------------------------------------

def test_artefact_renders_provenance_and_the_placeholder_warning():
    spec = importlib.util.spec_from_file_location(
        "run_b4", ROOT / "scripts" / "run_b4.py"
    )
    run_b4 = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(run_b4)

    measured = run_b4._provenance(_data()["profiles"]["measured"]["source"])
    assert "Open-Meteo" in measured and "1991-2020" in measured
    assert "Frankfurt" in measured, "the sites must be named, not implied"

    invented = run_b4._provenance(_data()["profiles"]["synthetic"]["source"])
    assert "invented" in invented and "Not a measurement" in invented


def test_region_file_is_ascii_and_stays_english():
    text = REGIONS_PATH.read_text(encoding="utf-8")
    offenders = sorted({char for char in text if ord(char) > 127})
    assert offenders == [], f"non-ASCII characters in the region table: {offenders}"



def _builder():
    spec = importlib.util.spec_from_file_location("build_weather_regions", BUILDER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module
