# AGENTS.md - Switchyard Logistics Coding Agent Contract

## Architecture Invariants

1. Event-Agnostic Gate: Decisions evaluate physical state bounds and formal constraints directly. No named event strings drive branches or gate logic. See `docs/06_EVENT_AGNOSTIC_GATE.md` (SW-06).
2. Integer Micro-Units Only: All physical quantities, time intervals, and temperatures are represented as fixed-point integers (minutes and micro-degrees Celsius). No floating-point arithmetic is permitted in evaluation or decision paths.
3. Dual-Engine Bit-Exact Parity: The Python reference model (`src/switchyard/`) and the Rust replay core (`engine/`) must produce bit-exact identical verdicts across all 300 pre-registered test instances.
4. Clean-Room Provenance & ASCII-Only Docs: All repository documentation and code comments must remain 100% 7-bit ASCII (ord <= 127). Decorative unicode, emoji, informal register (tokens like CEO, Boss, lol, haha), and internal system paths are strictly forbidden.
5. Fail-Closed Verification: Any violation of physical bounds, metadata constraints, or numerical tolerances must reject immediately.

## Mandatory Verification Commands

Before committing any changes, run the following verification gates:

```bash
# 1. Full Python test suite (must pass all 114 tests)
py -3.13 -m pytest -q

# 2. Native Rust test suite
cd engine && cargo test && cd ..

# 3. Corral static analysis and invariant check (must report 0 findings)
py -3.13 -m corral.cli check .
```
