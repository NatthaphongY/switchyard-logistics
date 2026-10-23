# Gate B4 measurement

Seed 20261023, 300 paired scenarios, intensity 1.0, elapsed 12.85 s, Python 3.13.3.

| Metric | Baseline | Composed | Effect (95 percent CI) |
|---|---|---|---|
| Unsafe control actions per scenario | 12.223 | 10.297 | 15.76 pp fewer (13.47 to 18.19) |
| Scenarios with zero unsafe actions | 0.0033 | 0.0067 | - |
| Excursion minutes per scenario | 28.4 | 16.5 | 45.37 percent fewer (23.15 to 67.59) |
| Blocking findings per scenario | 9.487 | 7.653 | 1.58 to 1.833 |
| Plans blocked outright | 0.99 | 0.9733 | - |
| Transport cost per scenario | 106.23 | 104.76 | - |

Decision: **SEPARATES** (rule: uca CI lower bound at least 15 pp OR excursion CI lower bound at least 10 percent, with blocks not worse). Priced planner selected in 224 of 300 scenarios.
