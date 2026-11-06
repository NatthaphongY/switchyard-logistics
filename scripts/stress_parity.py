"""Stress and robustness evidence for the gate core (SW-10 section 5).

Four questions, one command:

  1. Bit-exact parity: does the Rust core reproduce every Python verdict over
     hundreds of repeated passes, with zero mismatches?
  2. Determinism: does the Python reference produce the identical tuple on
     repeated evaluation of the same instance?
  3. Hostile input: does the core survive truncated, duplicated, misspelled,
     absurd and non-ASCII instances without panicking?
  4. Memory and liveness: does a long run finish, and does resident memory stay
     bounded rather than climb?

Usage:
    py -3.13 -X utf8 scripts/stress_parity.py --repeats 200
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from switchyard.evaluate import prepare  # noqa: E402
from switchyard.gate import evaluate  # noqa: E402
from switchyard.model import load_thresholds  # noqa: E402
from switchyard.planners import plan_remedied  # noqa: E402
from switchyard.scenarios import scenario  # noqa: E402

ENGINE = ROOT / "engine" / "target" / "release" / "switchyard-core.exe"
INSTANCES = ROOT / "evidence" / "instances.txt"

HOSTILE = {
    "empty.txt": "",
    "truncated.txt": "INSTANCE 0\nNET broken 1440\nNODE N00 90\n",
    "duplicate.txt": (
        "INSTANCE 0\nNET dup 1440\n"
        "NODE N00 90 40.000000 1 ambient|chilled\n"
        "NODE N00 90 40.000000 1 ambient\n"
        "CONS C00 N00 N01 4.000000 chilled 0 600 0\n"
        "FLAGS 0 0 - - - - 1 1 1 1\nEND\n"
    ),
    "absurd.txt": (
        "INSTANCE 0\nNET absurd 1440\n"
        "NODE N00 90 -40.000000 1 ambient\n"
        "LANE L000 N00 N00 road 0 0.000000 0.000000 0 0 0 0\n"
        "CONS C00 N00 N00 -4.000000 chilled -10 0 0\n"
        "FLAGS -5 -1 - - - - 0 0 0 0\nEND\n"
    ),
    "unicode.txt": (
        "INSTANCE 0\nNET \u0422\u0435\u0441\u0442 1440\n"
        "NODE \u0391\u0392\u0393 90 40.000000 1 ambient\n"
        "CONS \u0433\u0440\u0443\u0437 \u0391\u0392\u0393 \u0391\u0392\u0393 4.000000 chilled 0 600 0\n"
        "FLAGS 0 0 - - - - 1 1 1 1\nEND\n"
    ),
    "garbage.txt": "FLAGS\nPLANLEG\nNODE\n\x00\x01\x02\nEND\nEND\n",
}


def _thresholds():
    payload = json.loads((ROOT / "config" / "thresholds.json").read_text(encoding="utf-8"))
    payload.pop("_comment", None)
    payload.pop("version", None)
    return load_thresholds(payload)


def _run_engine(path: Path, repeats: int, threads: int, timeout: float = 120.0):
    started = time.perf_counter()
    completed = subprocess.run(
        [str(ENGINE), "--instances", str(path), "--threads", str(threads), "--repeat", str(repeats)],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return completed, time.perf_counter() - started


def main() -> int:
    parser = argparse.ArgumentParser(description="Stress the gate core")
    parser.add_argument("--repeats", type=int, default=200)
    parser.add_argument("--threads", type=int, default=8)
    parser.add_argument("--json-only", action="store_true")
    args = parser.parse_args()

    if not ENGINE.exists():
        print(f"engine not built: {ENGINE}")
        return 2

    thresholds = _thresholds()
    evidence: dict = {"repeats": args.repeats, "threads": args.threads}

    # 1. Python determinism: evaluate every instance, then evaluate again.
    def signature() -> list:
        out = []
        for index in range(300):
            network, event = scenario(20261023 + index)
            plan = prepare(plan_remedied(network, thresholds, event=event), event)
            release = evaluate(network, plan, event, thresholds)
            out.append((release.verdict, release.unsafe_control_actions, release.excursion_total))
        return out

    first = signature()
    evidence["python_deterministic"] = first == signature()
    evidence["python_instances"] = len(first)

    # 2. Bit-exact parity across many repeated passes.
    completed, elapsed = _run_engine(INSTANCES, args.repeats, args.threads)
    summary = completed.stdout.strip().splitlines()[0] if completed.stdout else ""
    fields = dict(item.split("=", 1) for item in summary.split() if "=" in item)
    evidence["parity"] = {
        "exit_code": completed.returncode,
        "mismatches": int(fields.get("mismatches", -1)),
        "checked": int(fields.get("checked", -1)),
        "per_pass_seconds": float(fields.get("per_pass", 0.0)),
        "throughput_per_second": float(
            fields.get("throughput", "0/s").strip().rstrip("/s") or 0.0
        ),
        "passes": args.repeats,
        "wall_seconds": round(elapsed, 3),
    }

    # 3. Hostile input: no panic, bounded exit code, no hang.
    hostile = {}
    for name, content in HOSTILE.items():
        target = ROOT / "evidence" / f"hostile_{name}"
        target.write_text(content, encoding="utf-8")
        try:
            result, _ = _run_engine(target, 1, 1, timeout=30.0)
            stderr = (result.stderr or "").lower()
            hostile[name] = {
                "exit_code": result.returncode,
                "panicked": "panic" in stderr,
                "bounded": result.returncode in (0, 2),
            }
        except subprocess.TimeoutExpired:
            hostile[name] = {"exit_code": None, "panicked": False, "bounded": False}
        finally:
            target.unlink(missing_ok=True)
    evidence["hostile"] = hostile

    # 4. Liveness and memory ceiling, measured from the operating system.
    peak_kb = 0
    started = time.perf_counter()
    process = subprocess.Popen(
        [
            str(ENGINE), "--instances", str(INSTANCES), "--threads", str(args.threads),
            "--repeat", str(max(args.repeats, 50)),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    while process.poll() is None:
        listing = subprocess.run(
            ["tasklist", "/FI", f"PID eq {process.pid}", "/FO", "CSV", "/NH"],
            capture_output=True, text=True, timeout=10,
        ).stdout
        cells = listing.strip().strip('"').split('","')
        if len(cells) >= 5:
            clean_mem = cells[4].replace(",", "").replace(" K", "").strip()
            if clean_mem.isdigit():
                peak_kb = max(peak_kb, int(clean_mem))
        time.sleep(0.05)
    evidence["liveness"] = {
        "finished": process.returncode == 0,
        "wall_seconds": round(time.perf_counter() - started, 3),
        "peak_resident_mb": round(peak_kb / 1024.0, 2),
    }

    ok = (
        evidence["python_deterministic"]
        and evidence["parity"]["mismatches"] == 0
        and evidence["parity"]["exit_code"] == 0
        and all(entry["bounded"] and not entry["panicked"] for entry in hostile.values())
        and evidence["liveness"]["finished"]
    )
    evidence["ok"] = ok

    (ROOT / "evidence" / "STRESS.json").write_text(
        json.dumps(evidence, indent=2, sort_keys=True), encoding="utf-8"
    )
    document = "\n".join(
        [
            "# Stress and robustness evidence",
            "",
            f"Passes: {args.repeats} - threads: {args.threads}",
            "",
            f"- Python determinism: {'PASS' if evidence['python_deterministic'] else 'FAIL'}",
            f"- Bit-exact parity: {evidence['parity']['checked']} checks, "
            f"{evidence['parity']['mismatches']} mismatches, "
            f"{evidence['parity']['throughput_per_second']:.0f}/s",
            "- Hostile inputs: "
            + ", ".join(
                f"{name}={'ok' if entry['bounded'] and not entry['panicked'] else 'FAIL'}"
                for name, entry in hostile.items()
            ),
            f"- Liveness: {'PASS' if evidence['liveness']['finished'] else 'FAIL'} "
            f"({evidence['liveness']['wall_seconds']} s, peak "
            f"{evidence['liveness']['peak_resident_mb']} MB resident)",
            "",
            f"Overall: {'PASS' if ok else 'FAIL'}",
        ]
    )
    (ROOT / "evidence" / "STRESS.md").write_text(document + "\n", encoding="utf-8")
    if not args.json_only:
        print(document)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
