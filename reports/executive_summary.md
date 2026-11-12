# Executive summary

**Question:** How should an e-commerce marketplace prioritise operational improvements to reduce delivery delays and improve customer satisfaction?

**Data:** Olist Brazilian E-Commerce Public Dataset. 99,441 orders across 9 related tables; analysis window Jan 2017 – Aug 2018 (20 complete months). The scenario and stakeholders are hypothetical; every number is computed from the data by a tested, reproducible pipeline.

## The answer in one line
Fix *where* delays concentrate: a few delivery lanes (led by São Paulo → Rio de Janeiro), three peak months, and a small group of sellers who miss handoff deadlines. Prove the effect with a lane pilot before scaling.

## Five findings
| # | Finding | Evidence grade |
|---|---|---|
| 1 | 6.8% of delivered orders miss the promised date. Late orders get 1–2 star reviews 62% of the time, against 9% when on time. The gap holds within the same seller (52.9 pp) and under regression controls (51.1 pp). | Robust association |
| 2 | 72% of late orders were handed to the carrier on time. The delay accrues after handoff (median transit 7.1 days vs. 1.8 days for seller handoff). | Observed |
| 3 | 15 lanes = 88% of excess late orders on 22% of volume. SP→RJ runs 14.3% late against 5.25% expected for its distance (2.7×). | Observed (standardised) |
| 4 | Nov 2017, Feb 2018 and Mar 2018 produced 48% of late orders. The Feb–Mar cause cannot be identified from the data. | Observed |
| 5 | Seller deadline misses (8.9% of orders) quadruple the late rate. 77% of misses come from 10% of sellers. | Association |

## Recommendations (impact vs. effort)
1. **Lane recovery pilot** (SP→RJ, SP→ES first; control lanes) — medium effort, highest concentration.
2. **Peak-season playbook** before November — medium effort.
3. **Seller deadline alerts and plans for 57 sellers** — low effort, quick win.
4. Enablers: one KPI owner and a weekly dashboard review; **capture the carrier ID on every order**.

Deprioritised: lengthening promises (backtest: 7.83% → 7.45% at equal promise), late-delivery retention campaigns (small effect).

## Scenario (not a forecast)
At base assumptions, the late rate falls from 7.9% to 5.3% in the baseline year (range 6.4% to 4.3%), about 1,800 fewer late orders a year. If only the November peak is predictable, the base case is about 6.1%. Proposed staged target: **≤ 6% in two quarters, ≤ 5% in twelve months.** No ROI is stated, because the dataset has no cost or margin data.

## Limitations
Observational data (no proven causation); 2016–18 data; no carrier identifier; no cost data. Each limitation has a mitigation in `docs/11_risk_register.md`.
