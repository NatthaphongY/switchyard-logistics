"""Gate-only throughput of the reference implementation.

Planning is excluded from the timing so the number is comparable with the Rust
core, which replays plans rather than producing them. Both sides evaluate the
same instances.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from switchyard.evaluate import prepare  # noqa: E402
from switchyard.gate import evaluate  # noqa: E402
from switchyard.model import load_thresholds  # noqa: E402
from switchyard.planners import plan_greedy  # noqa: E402
from switchyard.scenarios import scenario  # noqa: E402


def main() -> int:
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 300
    payload = json.loads((ROOT / "config" / "thresholds.json").read_text(encoding="utf-8"))
    payload.pop("_comment", None)
    payload.pop("version", None)
    thresholds = load_thresholds(payload)

    prepared = []
    for index in range(count):
        network, event = scenario(20261023 + index)
        plan = prepare(plan_greedy(network, thresholds), event)
        prepared.append((network, plan, event))

    started = time.perf_counter()
    for network, plan, event in prepared:
        evaluate(network, plan, event, thresholds)
    elapsed = time.perf_counter() - started
    print(
        f"python gate: instances={count} seconds={elapsed:.4f} "
        f"per_instance_ms={1000 * elapsed / count:.3f} throughput={count / elapsed:.0f}/s"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
