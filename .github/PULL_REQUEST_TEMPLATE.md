## Summary

Provide a concise description of the changes proposed in this pull request and the rationale behind them.

## Verification Checklist

Please verify that all project invariants hold before requesting review:

- [ ] Python test suite passes (`py -3.13 -m pytest -q` -> 114 passed)
- [ ] Rust engine tests pass (`cd engine && cargo test`)
- [ ] Structural audit passes with zero findings (`py -3.13 -m corral.cli check .`)
- [ ] No non-ASCII characters introduced in documentation or tracked files
- [ ] Normative compliance with SW-06 maintained
- [ ] Bit-exact parity between Python reference and Rust core preserved
