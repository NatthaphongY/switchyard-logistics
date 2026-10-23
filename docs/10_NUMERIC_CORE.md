# SW-10  -  Numeric Core: Fixed Point, Two Implementations, Measured Speed

| Field | Value |
|---|---|
| Document ID | SW-10 |
| Kind | Repository document (published) |
| Version | 1.0 |
| Status | Normative for arithmetic and conformance; measured numbers dated 2026-10-23 |
| Date | 2026-10-23 |
| Related documents | SW-06 for the gate, SW-05 for reproduction |
| Precedent reused | ADR-001 of the internal fixed-point engine (integer arithmetic and stream derivation) |

## 1. Decision

All decisions in the gate and the planners use integers. Money and quantity are
held in micro-units (10^-6 of the base unit, 64-bit). Time is integer minutes.
Ratios are raw Q16.16 integers. Floating point appears only in the transport
format and in reports, never in a comparison that changes a verdict.

This is not a stylistic preference. Three properties follow, and each is required
by a claim already made in this programme.

1. A verdict must be reproducible byte for byte (SW-06 section 9). Integer
   arithmetic gives that on every platform and in every language; floating point
   gives it only if every implementation rounds identically, which no specification
   can promise.
2. The conformance gate must be checkable by a second implementation. Two
   independent implementations that agree on integers is evidence; two that agree
   on floats within an epsilon is an argument.
3. A fixed-point core can later be ported to a shader without changing the meaning
   of a number. Floating point cannot.

## 2. What was reused, and from where

An earlier in-house fixed-point engine locked these decisions in its ADR-001.
The engine is not distributed with this programme, so the table cites the
decision rather than a file path: a reader of this document needs the contract,
not the internal layout of another project.

| Reused | Origin | What it gives this programme |
|---|---|---|
| Q16.16 fixed point, 64-bit accumulator, `MulDiv` guard, integer Newton square root | ADR-001 of the internal engine | The arithmetic contract, including the rule that floats are forbidden in simulation logic |
| xorshift64* with stream derivation, `FromStream(tick, tag)` and `Fork(tag)` | ADR-001 of the internal engine | One random stream any language can reproduce from the same seed |
| The rule that money at scale needs Q32.32 | ADR-001 of the internal engine | Money and quantity in micro-units, not Q16.16 |

The random stream is implemented in `src/switchyard/rng.py` as
`StreamRandom`, including a shim that keeps the call sites unchanged. The Rust
core uses the same algorithm, so a scenario and a plan can be reproduced in
either language.

## 3. What changed in the reference implementation

| Change | Reason |
|---|---|
| Capacity converted to integer micro-units before the maximum flow | Removes the only float comparison in the gate that could differ across languages |
| Demand compared in micro-units against the integer flow value | Same |
| Generator consumes `StreamRandom` instead of the interpreter generator | Cross-language reproducibility |
| Excursion, dwell, slack, lateness are integer minutes | Enforced by the integer flow path |

Thresholds remain in `config/thresholds.json`. The Rust core carries two
constants (handoff budget 90 minutes, freshness limit 240 minutes) because it has
no JSON dependency; the conformance test fails if the two drift apart.

## 4. Conformance result, 2026-10-23

Command sequence, reproducible on any machine with Python 3.13 and a Rust
toolchain:

    py -3.13 -X utf8 scripts/export_instances.py --scenarios 300
    cargo build --release --offline            (in engine)
    engine/target/release/switchyard-core.exe --instances evidence/instances.txt --threads 1 --repeat 20

Observed result, 300 instances, twenty passes each:

    instances=300 threads=1 repeat=20 checked=300 mismatches=0

Agreement covers the verdict string, the number of distinct unsafe control
actions (counted per consignment), total excursion minutes, and the number of
blocking findings. A mismatch is a specification defect, not a rounding failure,
because no float comparison can differ between the two paths.

## 5. Measured throughput

Same 300 instances, same machine, gate evaluation only, planning excluded.

| Implementation | Threads | Instances per second | Time per instance | Relative |
|---|---|---|---|---|
| Python 3.13 reference | 1 | 305 | 3.28 ms | 1.0 x |
| Rust core, release, LTO | 1 | 16,302 | 0.061 ms | 53 x |
| Rust core, release, LTO | 8 | 34,011 | 0.029 ms | 111 x |

The Rust path is fast enough to sweep parameter grids: one million gate
evaluations take about 29 seconds on eight threads instead of 55 minutes in
Python.

The eight-thread figure shows the limit of this workload, which is small enough per
instance that thread scheduling dominates beyond a few cores. The 8-thread number
moved from 28,435 to 34,011 per second when the parser was made total (no bounds
panic on malformed input), because a malformed line no longer aborts a worker.

These are gate numbers. The planners remain in Python: the full pipeline of 300
scenarios with three planners plus the eight-group ablation takes 47.8 seconds,
and porting the planner to Rust is the next step, not a finished claim.

## 6. Position on compute shaders

A compute shader is the right tool for one job here and the wrong tool for another,
and the difference is exactness.

| Job | Tool | Reason |
|---|---|---|
| Release decision and hash | Integer CPU code (Rust core, C# engine, Python reference) | A shader has no 64-bit integer product and no exact decimal; a hash computed in f32 cannot be reproduced |
| Monte Carlo over the cascade, millions of parameter draws | Compute shader (WGSL) with Q16.16 packed in 32-bit words | Throughput matters and a statistical answer tolerates quantisation, provided the precision ceiling is stated |

The precision ceiling, stated plainly: with Q16.16 ratios and 32-bit accumulation,
a million-draw sweep resolves differences above roughly 10^-4 relative. Any
comparison finer than that must run on the integer path. This is why the release
hash is never produced on the graphics processor.

## 7. What is not proven

1. The Rust core replays plans; it does not yet plan. Planning speed is unmeasured.
2. The parity result covers 300 synthetic instances generated by this programme. It
   is not evidence about a real corridor.
3. Fixed point removes rounding ambiguity; it does not remove modelling error. A
   wrong model is exactly reproducible.

