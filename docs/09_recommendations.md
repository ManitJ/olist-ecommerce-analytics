# Prioritised recommendations

## How priority was set
- **Impact** is evidence-based. It uses the scenario base case (late-rate reduction in the baseline year) and the evidence grade of the underlying finding.
- **Effort** is a **qualitative judgement**, because the dataset has no cost data. It is rated on the number of teams involved, any need for external negotiation, any need for new data or systems, and time to first result.
- Both should be revisited with Logistics and Finance in discovery (`02_stakeholder_analysis.md`).

## Impact vs. effort

| # | Recommendation | Impact (base case) | Evidence | Effort | Priority |
|---|---|---|---|---|---|
| R1 | **Lane recovery programme.** Weekly lane scorecard; carrier performance reviews on lanes that underperform their distance-matched expectation (SP→RJ, PR→RJ, SP→ES, SP→BA, SP→AL); staggered pilot | −0.84 pp (−0.42 to −1.27). Top 15 lanes = 88% of excess late orders on 22% of volume | Observed concentration plus a distance-standardised anomaly (F3) | **Medium.** Carrier negotiation; needs carrier ID (R5) | **1: Do first (pilot)** |
| R2 | **Peak-season playbook.** Capacity commitments 6 weeks ahead of November; earlier seller cut-offs; temporary promise buffer on flagged lanes in peak weeks | −1.16 pp (−0.73 to −1.75). 3 months = 48% of late orders | Observed (F4). Cause of the Feb–Mar spike unknown | **Medium.** Cross-team, seasonal; one cycle per year to learn | **2: Plan now for the next peak** |
| R3 | **Seller handoff programme.** Automated alert 24 h before the shipping limit; performance plans for the 57 "Intervene" sellers | −0.79 pp (−0.39 to −1.19). Misses quadruple the late rate | Association (F5) | **Low.** Uses existing timestamps; 57 sellers is a manageable caseload | **3: Quick win** |
| R4 | **Promise-reliability KPI and weekly operating review.** Single owner; dashboard pages 1–3 | Enabler, with no direct effect; it is how R1–R3 are steered and measured | — | **Low.** Package built (`dashboard/`) | **Do immediately** (pre-requisite) |
| R5 | **Capture carrier ID and tracking events per order** | Enabler for R1 and for any root cause after handoff | Data gap (DR-1, DR-2) | **Medium.** Systems / integration | **Start now, in parallel** |
| R6 | Recalibrate delivery promises by route | Low: −0.4 pp at equal promise length (backtest) | Observed, out of sample (F7) | Medium | **Deprioritise.** Peak buffers only (inside R2) |
| R7 | Proactive delay notifications to customers | Unknown | **Hypothesis**; no supporting data | Low–Medium | **Test only** (A/B test after R5 provides tracking data) |
| R8 | Retention campaigns aimed at customers who had a late first order | Very small: about 46 repeat customers over 20 months | Association (F8) | Low | **Do not prioritise** |

```
          LOW EFFORT                         MEDIUM EFFORT
HIGH   |  R3 Seller handoff (quick win)    | R1 Lane recovery (pilot first)    |
IMPACT |                                   | R2 Peak playbook                  |
       +-----------------------------------+-----------------------------------+
LOW /  |  R4 KPI & review (enabler)        | R5 Carrier data (enabler)         |
ENABLE |  R8 Retention (skip)              | R6 Promise recalibration (skip)   |
       |  R7 Notifications (test)          |                                   |
```

## Why R1 comes before R3, even though R3 is cheaper
R3 is the fastest win and should start immediately. But R1 targets the larger and more concentrated source of lateness: post-handoff delay, which accounts for 72% of late orders. It is also where a pilot can produce **measured** causal evidence (a staggered lane rollout) to replace the scenario assumptions. In practice R3 and R4 start in week 1, and R1 runs as the flagship pilot.

## Combined expectation
R1 + R2 + R3, with overlap removed: late rate **7.86% → 5.34%** (range 6.40% to 4.29%) in the baseline year. This does **not** reach 5% in the base case. The charter target is staged accordingly. See `08_scenario_analysis.md`.

## What we are explicitly not recommending, and why
- **No ROI or savings figures.** The data has no cost or margin. Inventing them would undermine the credibility of everything else.
- **No large-scale promise lengthening.** It would lower the late rate on paper while likely hurting conversion (unmeasured).
- **No seller penalties before alerts exist.** Sellers currently get no advance warning, as far as the data shows. Enforcement should follow enablement.
