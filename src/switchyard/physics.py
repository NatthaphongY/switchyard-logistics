"""Physical layers imported into the cold-chain model (SW-11).

The programme borrows mechanisms from fields that already solved the same
structural problem, and states the domain of validity of each borrowing.

  1. Queueing theory (Erlang / Kingman): a station near saturation does not slow
     down linearly, it collapses. Delay grows like 1 / (1 - rho), so a gate that
     only compares throughput with demand misses the last five percent.
  2. Traffic flow (Lighthill-Whitham-Richards): a convoy on a congested lane
     moves at the shockwave speed, not the free-flow speed.
  3. Heat transfer (Newton cooling) and reaction kinetics (Arrhenius): an
     excursion is not a count of minutes, it is an accumulated dose.
  4. Reliability theory (series / parallel systems): a route is a series system;
     a route with a booked backup mode is a parallel system.
  5. Epidemiology (SIR final size): a cascade saturates like an outbreak; the
     final size is a function of R0 alone, which is an analytic sanity check.
  6. Financial risk (expected shortfall): the tail matters more than the mean.

Two numeric regimes, deliberately separated:

  * ``continuous`` functions use f64 and exist for reporting and tests. They are
    never called from the decision path.
  * ``integer`` functions use integer arithmetic only and are the decision path.
    They are mirrored in the Rust core, so all operands are non-negative: Python
    floor division and Rust truncating division then agree exactly.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

PERMILLE = 1000
MICRO = 1_000_000

_DEFAULT_PATH = Path(__file__).resolve().parents[2] / "config" / "physics.json"


@dataclass(frozen=True)
class Physics:
    queue: dict
    thermal: dict
    traffic: dict
    reliability: dict
    epidemic: dict
    finance: dict
    service: dict
    cost: dict

    @classmethod
    def load(cls, path: Optional[Path] = None) -> "Physics":
        target = Path(path or _DEFAULT_PATH)
        try:
            payload = json.loads(target.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            raise ValueError(f"Failed to load physics configuration from {target}: {e}") from e
        return cls(
            queue=payload["queue"],
            thermal=payload["thermal"],
            traffic=payload["traffic"],
            reliability=payload["reliability"],
            epidemic=payload["epidemic"],
            finance=payload["finance"],
            service=payload["service"],
            cost=payload["cost"],
        )

    @property
    def delay_table(self) -> Tuple[int, ...]:
        return tuple(int(value) for value in self.queue["delay_factor_permille"])

    @property
    def mode_availability(self) -> Dict[str, int]:
        return {
            mode: int(value)
            for mode, value in self.reliability["mode_availability_permille"].items()
        }


_CACHE: Optional[Physics] = None


def physics() -> Physics:
    global _CACHE
    if _CACHE is None:
        _CACHE = Physics.load()
    return _CACHE


# ---------------------------------------------------------------------------
# Continuous models: reporting, plots and the conservativeness test only
# ---------------------------------------------------------------------------
def kingman_wait_min(
    utilisation: float,
    service_min: float,
    servers: int = 1,
    ca2: float = 1.0,
    cs2: float = 1.25,
) -> float:
    """Expected queue wait for GI/G/c in the Allen-Cunneen form.

    Returns ``inf`` at or beyond saturation rather than a large finite number, so
    a caller cannot mistake collapse for slowness.
    """
    if servers < 1:
        raise ValueError("servers must be at least one")
    if utilisation >= 1.0:
        return math.inf
    if utilisation <= 0.0:
        return 0.0
    exponent = math.sqrt(2.0 * (servers + 1)) - 1.0
    numerator = utilisation ** exponent
    denominator = servers * (1.0 - utilisation)
    return (numerator / denominator) * ((ca2 + cs2) / 2.0) * service_min


def little_law(arrivals_per_hour: float, time_in_system_h: float) -> float:
    """L = lambda * W. Used to report queue length from a measured wait."""
    return arrivals_per_hour * time_in_system_h


def shockwave_speed_kmh(
    density_up: float, density_down: float, flow_up: float, flow_down: float
) -> float:
    """LWR kinematic wave speed between two traffic states."""
    if density_down == density_up:
        return 0.0
    return (flow_down - flow_up) / (density_down - density_up)


def triangular_delay_min(length_km: float, density_per_km: float) -> float:
    """Delay of one lane under a triangular fundamental diagram."""
    cfg = physics().traffic
    jam = float(cfg["jam_density_veh_per_km"])
    cap_flow = float(cfg["capacity_veh_per_hour"])
    free_speed = float(cfg["free_flow_kmh"])
    if density_per_km >= jam:
        return math.inf
    if density_per_km <= 0.0:
        return 0.0
    free_time = (length_km / free_speed) * 60.0
    flow = cap_flow * (1.0 - density_per_km / jam)
    if flow <= 1e-9:
        return math.inf
    speed = flow / density_per_km
    if speed >= free_speed:
        return 0.0
    return (length_km / max(speed, 1e-6)) * 60.0 - free_time


def newton_temperature_c(
    start_c: float,
    ambient_c: float,
    minutes: float,
    u_value: float,
    area_m2: float,
    mass_kg: float,
    cp_kj_per_kgk: float,
    cooling_w: float = 0.0,
) -> float:
    """Container temperature under Newton cooling with an active cooling term."""
    if mass_kg <= 0 or cp_kj_per_kgk <= 0:
        return ambient_c
    heat_capacity_j_per_k = mass_kg * cp_kj_per_kgk * 1000.0
    gain_w_per_k = u_value * area_m2
    if gain_w_per_k <= 0:
        return start_c
    steady_state_c = ambient_c - cooling_w / gain_w_per_k
    tau_s = heat_capacity_j_per_k / gain_w_per_k
    decay = math.exp(-minutes * 60.0 / tau_s)
    return steady_state_c + (start_c - steady_state_c) * decay


def arrhenius_fraction_remaining(
    temperatures_c: Sequence[float],
    minutes_each: float,
    ea_j_per_mol: float,
    reference_c: float,
) -> float:
    """Fraction of potency remaining after a piecewise-constant history.

    Rate k(T) = exp(-Ea/R * (1/T - 1/T_ref)); the reference rate is normalised to
    one, so the result is a relative dose and not an absolute shelf life.
    """
    gas = physics().thermal["arrhenius"]["gas_constant_j_per_molk"]
    t_ref = reference_c + 273.15
    dose = 0.0
    for temperature_c in temperatures_c:
        kelvin = temperature_c + 273.15
        if kelvin <= 0:
            dose += minutes_each
            continue
        rate = math.exp(-(ea_j_per_mol / gas) * (1.0 / kelvin - 1.0 / t_ref))
        dose += rate * minutes_each
    return 1.0 / (1.0 + dose / 60.0)


def mean_kinetic_temperature_c(
    temperatures_c: Sequence[float], minutes_each: float = 1.0
) -> float:
    """Mean kinetic temperature, the pharmaceutical stability metric."""
    if not temperatures_c:
        return 0.0
    ea = physics().thermal["arrhenius"]["ea_j_per_mol"]
    gas = physics().thermal["arrhenius"]["gas_constant_j_per_molk"]
    mean_exp = sum(
        math.exp(-ea / (gas * (t + 273.15))) for t in temperatures_c
    ) / len(temperatures_c)
    return -ea / (gas * math.log(mean_exp)) - 273.15


def availability_series(availabilities: Iterable[float]) -> float:
    result = 1.0
    for value in availabilities:
        result *= value
    return result


def availability_parallel(availabilities: Sequence[float]) -> float:
    """Availability of a redundant set: one minus the product of failure rates."""
    product = 1.0
    for value in availabilities:
        product *= 1.0 - value
    return 1.0 - product


def availability_from_mtbf(mtbf_h: float, mttr_h: float) -> float:
    if mtbf_h <= 0:
        return 0.0
    return mtbf_h / (mtbf_h + mttr_h)


def sir_final_size(r0: float, tolerance: float = 1e-12, max_iterations: int = 10_000) -> float:
    """Final size of a simple SIR outbreak.

    ``s_inf`` solves s = exp(-R0 * (1 - s)). Used as an analytic sanity check on
    the simulated cascade: a cascade whose final size drifts far from this value
    is a modelling error, not a discovery.
    """
    if r0 <= 1.0:
        return 0.0
    s = 1.0 - 1e-9
    for _ in range(max_iterations):
        next_s = math.exp(-r0 * (1.0 - s))
        if abs(next_s - s) < tolerance:
            s = next_s
            break
        s = next_s
    return max(0.0, 1.0 - s)


def herd_immunity_threshold(r0: float) -> float:
    if r0 <= 1.0:
        return 0.0
    return 1.0 - 1.0 / r0


def expected_shortfall(losses: Sequence[float], alpha: float = 0.95) -> float:
    """Mean of the worst (1 - alpha) fraction of losses. Empty input yields zero."""
    if not losses:
        return 0.0
    ordered = sorted(losses)
    cut = max(1, int(round((1.0 - alpha) * len(ordered))))
    tail = ordered[-cut:]
    return sum(tail) / len(tail)


# ---------------------------------------------------------------------------
# Integer derivations: the decision path, mirrored 1:1 in the Rust core
# ---------------------------------------------------------------------------
def utilisation_permille(load_micro: int, capacity_micro: int, hours: int) -> int:
    """Station utilisation in per-mille. Saturated when capacity is unusable."""
    if load_micro <= 0:
        return 0
    if capacity_micro <= 0 or hours <= 0:
        return PERMILLE
    denominator = capacity_micro * hours
    return min(PERMILLE, (load_micro * PERMILLE) // denominator)


def queue_factor_permille(table: Sequence[int], utilisation: int) -> int:
    """Table lookup: bucket width is 50 per-mille, clamped at the last entry."""
    if not table:
        return PERMILLE
    if utilisation <= 0:
        return int(table[0])
    bucket = min(len(table) - 1, utilisation // 50)
    return int(table[bucket])


def thermal_dose_permille(
    uncontrolled_min: int,
    heat_gain_permille: int,
    protected: bool,
    credit_permille: int,
    budget_min: int,
) -> int:
    """Accumulated thermal dose in per-mille of the quality budget.

    ``heat_gain_permille`` scales nominal exposure by insulation and ambient
    delta. Protection credit is applied before the budget comparison, so a plan
    that pays for active cooling is rewarded in the same unit as the risk.
    """
    if budget_min <= 0:
        return PERMILLE
    exposure = max(0, uncontrolled_min) * max(0, heat_gain_permille)
    if protected:
        exposure = (exposure * max(0, PERMILLE - credit_permille)) // PERMILLE
    return (exposure * PERMILLE) // (max(0, budget_min) * PERMILLE)


def availability_permille(
    modes: Sequence[str], table: Dict[str, int], backup_mode: Optional[str] = None
) -> int:
    """Series availability of a route in per-mille.

    A booked backup mode upgrades the weakest series link into a parallel pair,
    which is why redundancy is priced rather than assumed.
    """
    if not modes:
        return 0
    factors = [int(table.get(mode, PERMILLE)) for mode in modes]
    if backup_mode:
        weakest = min(factors)
        backup = int(table.get(backup_mode, PERMILLE))
        failed_both = ((PERMILLE - weakest) * (PERMILLE - backup)) // PERMILLE
        factors[factors.index(weakest)] = PERMILLE - failed_both
    result = PERMILLE
    for factor in factors:
        result = (result * factor) // PERMILLE
    return max(0, min(PERMILLE, result))


def served_permille(served_micro: int, total_micro: int) -> int:
    if total_micro <= 0:
        return PERMILLE
    return min(PERMILLE, (max(0, served_micro) * PERMILLE) // total_micro)


def quantise(value: float) -> int:
    """Single rounding rule for floats entering the integer decision path.

    Round half away from zero, identical to ``f64::round`` in Rust, so an
    exported instance and its replay agree bit for bit.
    """
    scaled = value * MICRO
    if scaled >= 0:
        return int(math.floor(scaled + 0.5))
    return -int(math.floor(-scaled + 0.5))


def conservative_check(
    uncontrolled_min: int,
    heat_gain_permille: int,
    start_c: float,
    ambient_c: float,
    budget_min: int,
) -> Dict[str, float]:
    """Compare the linear dose budget with the Arrhenius estimate.

    Returns both numbers so a test can assert the gate is never *less* strict
    than the kinetic model: a gate that under-reports degradation would be worse
    than no gate at all.
    """
    cfg = physics().thermal
    temperature = newton_temperature_c(
        start_c=start_c,
        ambient_c=ambient_c,
        minutes=uncontrolled_min,
        u_value=cfg["u_value_w_per_m2k"],
        area_m2=cfg["area_m2"],
        mass_kg=cfg["mass_kg"],
        cp_kj_per_kgk=cfg["cp_kj_per_kgk"],
        cooling_w=0.0,
    )
    remaining = arrhenius_fraction_remaining(
        [temperature] * max(1, uncontrolled_min),
        minutes_each=1.0,
        ea_j_per_mol=cfg["arrhenius"]["ea_j_per_mol"],
        reference_c=cfg["arrhenius"]["reference_c"],
    )
    kinetic_dose_permille = int(round((1.0 - remaining) * PERMILLE))
    linear_dose_permille = thermal_dose_permille(
        uncontrolled_min, heat_gain_permille, False, 0, budget_min
    )
    return {
        "temperature_c": temperature,
        "remaining_fraction": remaining,
        "kinetic_dose_permille": kinetic_dose_permille,
        "linear_dose_permille": linear_dose_permille,
    }
