# Contributing to Switchyard

Thank you for your interest in contributing to Switchyard. This document outlines the standards, guidelines, and verification workflows required for all contributions.

## Architectural Principles

1. Event-Agnostic Gate: Evaluation decisions evaluate physical and institutional state directly. No string-based event dispatching or named event branches are allowed.
2. Integer Micro-Unit Arithmetic: Floating-point arithmetic is prohibited in compliance evaluation logic. All state calculations must use integer micro-units and integer minutes.
3. Bit-Exact Parity: The Python reference implementation and the Rust replay core must produce identical outputs on all scenarios.
4. Clean Documentation: All documentation must be plain ASCII (ord <= 127), formal in tone, and free of informal register or decorative markers.

## Development Workflow

### Prerequisites
- Python 3.13 or higher
- Rust 1.80 or higher (with Cargo)

### Setup
Clone the repository and install the development package in editable mode:

```bash
git clone https://github.com/NatthaphongY/switchyard-logistics.git
cd switchyard-logistics
pip install -e .
```

### Running Tests

Before submitting a pull request, ensure all test suites pass:

1. Python Verification Suite:
   ```bash
   py -3.13 -m pytest -q
   ```
   All 114 test cases must pass.

2. Rust Engine Verification Suite:
   ```bash
   cd engine
   cargo test
   cargo build --release
   cd ..
   ```

3. Code Quality & Invariant Gate:
   ```bash
   py -3.13 -m corral.cli check .
   ```
   Corral check must return 0 findings (0 blocking).

4. Parity and Stress Verification:
   ```bash
   py -3.13 -X utf8 scripts/stress_parity.py --repeats 200
   ```

## Pull Request Guidelines

- Branch names should be descriptive (e.g., `feature/gate-extension` or `fix/parity-edge-case`).
- Commit messages must follow conventional commit standards (`feat:`, `fix:`, `docs:`, `chore:`).
- Every PR must maintain full conformance with normative document SW-06.
