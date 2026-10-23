# Stress and robustness evidence

Passes: 200 - threads: 8

- Python determinism: PASS
- Bit-exact parity: 300 checks, 0 mismatches, 30915/s
- Hostile inputs: empty.txt=ok, truncated.txt=ok, duplicate.txt=ok, absurd.txt=ok, unicode.txt=ok, garbage.txt=ok
- Liveness: PASS (2.023 s, peak 10.36 MB resident)

Overall: PASS
