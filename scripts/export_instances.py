"""Export instances and composed plans for the Rust hot-path core.

The reference implementation stays in Python: it is the readable definition. The
Rust core replays the same instances to (a) prove the gate is specified well
enough to be implemented twice and (b) measure throughput without a Python
interpreter in the loop. Floats are exported at full precision so both sides
read identical inputs.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from switchyard.evaluate import prepare  # noqa: E402
from switchyard.gate import evaluate  # noqa: E402
from switchyard.model import Thresholds, load_thresholds  # noqa: E402
from switchyard.planners import plan_greedy, plan_priced, plan_remedied  # noqa: E402
from switchyard.scenarios import scenario  # noqa: E402
from switchyard.weather import apply as apply_weather, assess  # noqa: E402


def _flags(plan, event) -> str:
    precool = "|".join(sorted(cid for cid, ok in plan.pre_cool_verified.items() if ok)) or "-"
    disposition = "|".join(sorted(cid for cid, ok in plan.excursion_disposition.items() if ok)) or "-"
    estimate = "|".join(sorted(plan.excursion_estimate_min)) or "-"
    cost_red = "|".join(sorted(plan.cost_reduction_accepted)) or "-"
    escrow = "|".join(sorted(plan.escrowed)) or "-"
    backup = "|".join(f"{cid}:{mode}" for cid, mode in sorted(plan.backup_modes.items())) or "-"
    thermal = "|".join(sorted(plan.thermal_protection)) or "-"
    prepos = "|".join(f"{cid}:{qty:.6f}" for cid, qty in sorted(plan.prepositioned.items())) or "-"
    deferred = "|".join(sorted(plan.deferred)) or "-"
    return " ".join(
        [
            "FLAGS",
            str(plan.decision_age_min),
            str(plan.approvals_needed),
            precool,
            disposition,
            estimate,
            cost_red,
            "1" if plan.capacity_verified else "0",
            "1" if plan.documents_verified else "0",
            "1" if plan.counterparty_verified else "0",
            "1" if plan.border_permits_held else "0",
            "1" if plan.pre_authorised else "0",
            "1" if plan.input_refreshed else "0",
            "1" if plan.capacity_measured else "0",
            "1" if plan.out_of_band_verified else "0",
            escrow,
            backup,
            thermal,
            prepos,
            deferred,
        ]
    )


def _config_line(thresholds: Thresholds) -> str:
    from switchyard.physics import physics

    cfg = physics()
    fields = [
        f"queue_ceiling={thresholds.queue_ceiling_permille}",
        f"availability_floor={thresholds.availability_floor_permille}",
        f"service_floor={thresholds.service_floor_permille}",
        f"thermal_budget={thresholds.thermal_budget_permille}",
        f"protection_credit={int(cfg.thermal['protection_credit_permille'])}",
    ]
    for mode, value in sorted(cfg.mode_availability.items()):
        fields.append(f"mode_{mode}={value}")
    return "CONFIG " + " ".join(fields)


def main() -> int:
    parser = argparse.ArgumentParser(description="Export gate instances for the Rust core")
    parser.add_argument("--scenarios", type=int, default=300)
    parser.add_argument("--seed", type=int, default=20261023)
    parser.add_argument("--out", default=str(Path("evidence") / "instances.txt"))
    parser.add_argument(
        "--weather",
        action="store_true",
        help="Export instances with ambient conditions priced into heat_gain_permille",
    )
    args = parser.parse_args()

    thresholds_path = ROOT / "config" / "thresholds.json"
    try:
        payload = json.loads(thresholds_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, ValueError) as exc:
        raise ValueError(f"Invalid JSON in {thresholds_path}: {exc}") from exc
    payload.pop("_comment", None)
    payload.pop("version", None)
    thresholds: Thresholds = load_thresholds(payload)

    lines = [_config_line(thresholds)]
    for index in range(args.scenarios):
        network, event = scenario(args.seed + index)
        if args.weather:
            # The exported CONS line carries the re-priced integer, so the Rust
            # core replays the same instance without knowing weather exists.
            network = apply_weather(network, assess(event, seed=args.seed + index))
        plan = plan_greedy(network, thresholds)
        priced, _ = plan_priced(network, thresholds, event=event)
        remedied = plan_remedied(network, thresholds, event=event)
        best = None
        for candidate in (plan, priced, remedied):
            prepared = prepare(candidate, event)
            release = evaluate(network, prepared, event, thresholds)
            key = (release.blocks, release.unsafe_control_actions, release.excursion_total)
            if best is None or key < best[0]:
                best = (key, prepared, release)
        _, plan, release = best
        lines.append(f"INSTANCE {index}")
        lines.append(f"NET {network.name} {network.horizon_min}")
        for nid, node in sorted(network.nodes.items()):
            lines.append(
                f"NODE {nid} {node.dwell_p95_min} {node.capacity_per_hour:.6f} "
                f"{1 if node.assessed else 0} {'|'.join(node.classes)}"
            )
        for lane in network.lanes:
            lines.append(
                f"LANE {lane.id} {lane.src} {lane.dst} {lane.mode} {lane.travel_min} "
                f"{lane.capacity_per_hour:.6f} {lane.cost_per_unit:.6f} "
                f"{1 if lane.monitored else 0} {1 if lane.controlled else 0} "
                f"{lane.blocked_until_min} {1 if lane.cross_border else 0}"
            )
        for consignment in network.consignments:
            lines.append(
                f"CONS {consignment.id} {consignment.origin} {consignment.dest} "
                f"{consignment.qty:.6f} {consignment.temp_class} {consignment.ready_min} "
                f"{consignment.due_min} {consignment.excursion_allowance_min} "
                f"{consignment.heat_gain_permille} {consignment.quality_budget_min} "
                f"{consignment.prepositioned_qty:.6f}"
            )
        for leg in plan.legs:
            lines.append(
                f"PLANLEG {leg.consignment} {leg.lane} {leg.depart_min} "
                f"{1 if leg.party else 0} {1 if leg.door_confirmed else 0} {leg.container or '-'}"
            )
        lines.append(_flags(plan, event))
        lines.append(f"EVENT {event.get('notice_min')}")
        lines.append(
            f"EXPECT {release.verdict} {release.unsafe_control_actions} "
            f"{release.excursion_total} {release.blocks}"
        )
        lines.append("END")

    target = ROOT / args.out
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(lines) + "\n", encoding="ascii")
    print(f"exported {args.scenarios} instances to {target} ({target.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
