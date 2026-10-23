# BHR-RS-03  -  Evidence Register, 2026

| Field | Value |
|---|---|
| Document ID | BHR-RS-03 |
| Version | 2.0 |
| Status | Active, open for additions |
| Date | 2026-10-23 |
| Collection tool | `scripts/web_research.py` (free sources, no credentials) |
| Normative status | Informative; this register does not constitute business canon |

## 1. Rules for this register

1. Each entry MUST record a source and a retrieval or publication date.
2. Entries MUST be re-verified before any financial commitment or public claim.
3. Raw tool output MUST be retained under `logs/web_research/`.
4. An entry without a tier-one source MUST be marked accordingly.

## 2. Electronic design automation (workstream A, suspended)

| Entry | Source | Date |
|---|---|---|
| Market value USD 20.78 billion in 2026 rising to USD 30.67 billion in 2031, compound annual growth 8.1 per cent; Asia-Pacific largest and fastest growing; market concentration high | Mordor Intelligence | retrieved 2026-10-23, page updated 2026-10-14 |
| Acquisition of Ansys by Synopsys for USD 35 billion completed in 2025 | Mordor Intelligence, same analysis | retrieved 2026-10-23 |
| Joint model announced by OpenAI and Synopsys that operates electronic design automation tools | Tom's Hardware | published 2026-10-06 |
| Licence model shifting towards royalty and model revenue sharing | The Futurum Group | published 2026-10-02 |
| Industry position that the next requirement is evidence-driven automation | Semiconductor Engineering | published 2026-09-24 |
| Design agents described as entering mainstream adoption | Intelligent Living | published 2026-10-16 |
| Reinforcement learning research on floorplanning and routing continues | ResearchGate | 2026, exact date not stated in results |
| Reinforcement-learning placement methodology confirmed by a 2024 addendum | deepmind.google, nature.com | 2024, background only |
| Mask, verification, and tape-out costs reported as having escalated sharply, without figures | promwad.com | published 2026-10-22 |

Interpretation: the market grows slowly and is highly concentrated. Incumbent vendors are
already partnered with artificial-intelligence laboratories. The available position for a
new entrant is evidence and trust, not a new model.

## 3. Semiconductor demand

| Entry | Source | Date |
|---|---|---|
| Market passing the one trillion US dollar threshold on artificial-intelligence infrastructure | IDC | published 2026-04-29 |
| Long-range outlook described as a 2.3 trillion US dollar horizon | McKinsey | published 2026-09-18 |
| Record quarterly revenue reported, above expectations | Reuters | published 2026-10-07 |
| Outlook raised on artificial-intelligence demand | Yahoo Finance | published 2026-08-06 |
| Annual industry outlook | KPMG | published 2026-03-19 |

Interpretation: demand is expanding, which does not support the hypothesis that the
semiconductor industry will not survive. Design cost and complexity are rising faster than
margin, which supports the second half of that hypothesis: the constraint lies in the design
and tooling layer, not in the end market.

## 4. Cold chain logistics (workstream B, active)

| Entry | Source | Date |
|---|---|---|
| Market value USD 384.9 billion in 2026 rising to USD 555.4 billion in 2032, compound annual growth 6.34 per cent; temperature-controlled storage 52.21 per cent of the total | Mordor Intelligence | retrieved 2026-10-23, page updated 2026-10-14 |
| Approximately two thirds of Far East to Europe capacity returned to the Suez route | The Loadstar | published 2026-10-21 |
| Container transits through Suez recovering | Marine Link | published 2026-10-14 |
| Suez sailings above 50 per cent of pre-crisis levels | El Estrecho Digital | published 2026-10-14 |
| Full return to Suez expected within 2026 | Kuehne+Nagel report | published 2026-08-18 |
| Cautious return of large carriers while regional risk persists | Al-Monitor | published 2026-09-28 |
| Six healthcare corridors added between Europe, North America, and Asia | DHL Group | published 2026-10-12 |
| European cold-chain pharmaceutical booking digitised | FreightWaves | published 2026-10-15 |
| Direction stated as prediction rather than visibility | Logistics Viewpoints | published 2026-10-21 |
| Practical guidance on artificial intelligence in pharmaceutical supply chains | Pharmaceutical Commerce | published 2026-10-19 |
| General state of cold chain logistics | Thomasnet | published 2026-07-20 |

Interpretation: regional disruption risk is declining during 2026, so a product scoped to a
specific crisis will not sell. The gap is recalculation under temperature constraint.


## 5. Limitations of this collection round

1. Three queries returned empty result lists from the free search interface: cold chain
   market size 2026, freight rates for the Red Sea and Suez in 2026, and three-nanometre
   design cost. Direct page retrieval and news feeds were used instead. This is a limitation
   of free sources, not evidence of absence.
2. No tier-one estimate of chip design cost has been obtained. A tier-one source is required
   before any cost figure is used publicly.
3. No commercial lane, rate, or temperature data has been obtained, and none will be
   acquired under decision D-6. Workstream B therefore starts from open data and documented
   assumptions.

## 6. Reproduction

```powershell
py -3.13 -X utf8 scripts/web_research.py search "AI chip floorplanning routing 2026 reinforcement learning EDA" --limit 8
py -3.13 -X utf8 scripts/web_research.py search "AlphaChip DeepMind chip placement 2026 production adoption" --limit 6
py -3.13 -X utf8 scripts/web_research.py news "semiconductor industry 2026 outlook" --hl en --limit 8
py -3.13 -X utf8 scripts/web_research.py news "cold chain logistics pharma 2026" --hl en --limit 8
py -3.13 -X utf8 scripts/web_research.py news "Red Sea shipping Suez return 2026" --hl en --limit 6
py -3.13 -X utf8 scripts/web_research.py read "https://www.mordorintelligence.com/industry-reports/cold-chain-logistics-market" --chars 2200
py -3.13 -X utf8 scripts/web_research.py read "https://www.mordorintelligence.com/industry-reports/electronic-design-automation-eda-tools-market" --chars 2500
```
