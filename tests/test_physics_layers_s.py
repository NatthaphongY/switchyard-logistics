"""Physical layers: analytic checks, not smoke tests (SW-11).

Each test pins a property that the imported mechanism must have, so a future
"small optimisation" cannot quietly change the physics:

  * queueing collapses at saturation and behaves like M/M/1 below it;
  * the SIR final size reproduces textbook values;
  * Newton cooling converges to the ambient steady state;
  * Arrhenius degradation increases with temperature;
  * the integer dose is a conservative bound on the kinetic dose;
  * series availability is multiplicative and parallel availability is not;
  * integer rounding matches the Rust core's rounding rule exactly.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from switchyard.physics import (  # noqa: E402
    arrhenius_fraction_remaining,
    availability_from_mtbf,
    availability_parallel,
    availability_permille,
    availability_series,
    conservative_check,
    expected_shortfall,
    herd_immunity_threshold,
    kingman_wait_min,
    little_law,
    mean_kinetic_temperature_c,
    newton_temperature_c,
    physics,
    quantise,
    served_permille,
    sir_final_size,
    thermal_dose_permille,
    utilisation_permille,
)

MODE_TABLE = {"road": 993, "rail": 991, "sea": 985, "air": 980}


def test_kingman_is_infinite_at_saturation():
    assert math.isinf(kingman_wait_min(1.0, 10.0))
    assert math.isinf(kingman_wait_min(1.2, 10.0))


def test_kingman_matches_mm1_below_saturation():
    """With ca2 = cs2 = 1 and one server, Allen-Cunneen reduces to M/M/1."""
    for utilisation in (0.3, 0.5, 0.8):
        expected = utilisation / (1.0 - utilisation) * 12.0
        assert kingman_wait_min(utilisation, 12.0, 1, 1.0, 1.0) == pytest.approx(expected)


def test_kingman_is_monotone_in_utilisation():
    waits = [kingman_wait_min(rho, 10.0, 2) for rho in (0.1, 0.4, 0.7, 0.9)]
    assert waits == sorted(waits)


def test_little_law():
    assert little_law(20.0, 0.25) == pytest.approx(5.0)


def test_sir_final_size_matches_textbook_values():
    assert sir_final_size(2.0) == pytest.approx(0.7968, abs=5e-3)
    assert sir_final_size(1.5) == pytest.approx(0.5828, abs=5e-3)
    assert sir_final_size(0.9) == 0.0


def test_herd_immunity_threshold():
    assert herd_immunity_threshold(4.0) == pytest.approx(0.75)
    assert herd_immunity_threshold(1.0) == 0.0


def test_newton_cooling_converges_to_ambient():
    cfg = physics().thermal
    settled = newton_temperature_c(
        start_c=5.0,
        ambient_c=cfg["ambient_c"],
        minutes=10_000,
        u_value=cfg["u_value_w_per_m2k"],
        area_m2=cfg["area_m2"],
        mass_kg=cfg["mass_kg"],
        cp_kj_per_kgk=cfg["cp_kj_per_kgk"],
    )
    assert settled == pytest.approx(cfg["ambient_c"], abs=0.5)


def test_active_cooling_lowers_the_steady_state():
    cfg = physics().thermal
    kwargs = dict(
        start_c=5.0,
        ambient_c=cfg["ambient_c"],
        minutes=600,
        u_value=cfg["u_value_w_per_m2k"],
        area_m2=cfg["area_m2"],
        mass_kg=cfg["mass_kg"],
        cp_kj_per_kgk=cfg["cp_kj_per_kgk"],
    )
    passive = newton_temperature_c(**kwargs)
    active = newton_temperature_c(cooling_w=cfg["active_cooling_w"], **kwargs)
    assert active < passive


def test_arrhenius_degradation_increases_with_temperature():
    ea = physics().thermal["arrhenius"]["ea_j_per_mol"]
    reference = physics().thermal["arrhenius"]["reference_c"]
    cold = arrhenius_fraction_remaining([5.0] * 120, 1.0, ea, reference)
    warm = arrhenius_fraction_remaining([25.0] * 120, 1.0, ea, reference)
    hot = arrhenius_fraction_remaining([35.0] * 120, 1.0, ea, reference)
    assert cold > warm > hot


def test_mean_kinetic_temperature_lies_between_extremes():
    assert 5.0 < mean_kinetic_temperature_c([5.0, 25.0]) < 25.0


def test_series_and_parallel_availability():
    assert availability_series([0.99, 0.99, 0.99]) == pytest.approx(0.970_299)
    assert availability_parallel([0.9, 0.9]) == pytest.approx(0.99)
    assert availability_from_mtbf(99.0, 1.0) == pytest.approx(0.99)


def test_expected_shortfall_only_reads_the_tail():
    losses = [0.0] * 95 + [10.0] * 5
    assert expected_shortfall(losses, 0.95) == pytest.approx(10.0)
    assert expected_shortfall([], 0.95) == 0.0


# ---------------------------------------------------------------------------
# Integer decision path
# ---------------------------------------------------------------------------
def test_utilisation_is_saturated_when_capacity_is_unusable():
    assert utilisation_permille(5_000_000, 0, 24) == 1000
    assert utilisation_permille(5_000_000, 1_000_000, 0) == 1000


def test_utilisation_matches_hand_computation():
    # 5 units loaded, capacity 10 per hour over 24 hours -> 20.8 per-mille.
    assert utilisation_permille(5_000_000, 10_000_000, 24) == 20
    assert utilisation_permille(240_000_000, 10_000_000, 24) == 1000


def test_dose_is_linear_and_budget_normalised():
    # 100 min uncontrolled, heat gain 1000 per-mille, budget 200 min -> 500.
    assert thermal_dose_permille(100, 1000, False, 0, 200) == 500
    assert thermal_dose_permille(0, 1400, False, 0, 120) == 0


def test_protection_credit_reduces_dose_within_one_unit():
    """Two floor divisions can differ by one unit; the direction is what matters."""
    credit = int(physics().thermal["protection_credit_permille"])
    plain = thermal_dose_permille(180, 1100, False, credit, 210)
    protected = thermal_dose_permille(180, 1100, True, credit, 210)
    assert protected <= plain * (1000 - credit) // 1000 + 1
    assert protected < plain


def test_dose_with_zero_budget_fails_closed():
    assert thermal_dose_permille(10, 1000, False, 0, 0) == 1000


def test_availability_product_matches_float_version():
    integer = availability_permille(["road", "rail"], MODE_TABLE)
    floating = int(1000 * 0.993 * 0.991)
    assert abs(integer - floating) <= 1


def test_backup_mode_improves_availability():
    plain = availability_permille(["air"], MODE_TABLE)
    redundant = availability_permille(["air"], MODE_TABLE, "road")
    assert redundant > plain


def test_availability_of_empty_route_is_zero():
    assert availability_permille([], MODE_TABLE) == 0


def test_served_permille_guards():
    assert served_permille(0, 0) == 1000
    assert served_permille(7_000_000, 10_000_000) == 700
    assert served_permille(20_000_000, 10_000_000) == 1000


def test_quantise_rounds_half_away_from_zero_like_rust():
    assert quantise(1.0000005) == 1_000_001
    assert quantise(-1.0000005) == -1_000_001
    assert quantise(0.0) == 0


def test_linear_bound_is_conservative_against_kinetics():
    """The gate must never be *less* strict than the kinetic model it stands in for."""
    cfg = physics().thermal
    result = conservative_check(
        uncontrolled_min=240,
        heat_gain_permille=1200,
        start_c=5.0,
        ambient_c=cfg["ambient_c"],
        budget_min=120,
    )
    assert result["remaining_fraction"] < 1.0
    assert result["linear_dose_permille"] >= result["kinetic_dose_permille"]
