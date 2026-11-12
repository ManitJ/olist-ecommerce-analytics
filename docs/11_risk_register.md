# Risk register

Scale: Likelihood (L) and Impact (I), each 1 (low) to 3 (high). Score = L × I. Owners are hypothetical roles.

| ID | Risk | Category | L | I | Score | Mitigation | Owner | Trigger / early warning |
|---|---|---|---|---|---|---|---|---|
| RK-01 | **Correlation mistaken for causation.** Interventions reduce lateness, but reviews improve less than the scenario assumes. | Analytical | 2 | 3 | 6 | Staggered lane pilot with difference-in-differences; scenario labelled "assumes causality"; report review effects as ranges | BA / Analytics | Pilot lanes improve the late rate but not the 1–2 star rate |
| RK-02 | **Historical data (2016–18) no longer represents current operations** | Data | 3 | 2 | 6 | Rerun the pipeline on current data in Phase 0 (the pipeline is reproducible) | BI team | Current late rate or lane ranking differs materially |
| RK-03 | **No carrier ID**, so lane problems cannot be attributed to a carrier | Data | 3 | 2 | 6 | R5 data capture; lane-level reviews with all carriers until then | Logistics | Carrier ID coverage < 95% after week 8 |
| RK-04 | **Gaming the KPI:** promises lengthened to cut the "late" rate | Behavioural | 2 | 3 | 6 | Avg promised days as a guardrail (≤ +1 day); promise changes need sponsor approval | VP Ops | Avg promised days rises with no improvement in delivery days |
| RK-05 | Seller programme alienates high-revenue sellers (top 10% = 67% of revenue) | Commercial | 2 | 3 | 6 | Alerts before enforcement; account-managed plans for top sellers; tier rule needs ≥ 30 orders | Seller Success | Churn or volume drop among Intervene-tier sellers |
| RK-06 | Carriers resist lane SLAs or raise prices | Commercial | 2 | 2 | 4 | Present lane evidence (order counts, distance-matched gap); consider alternative carriers on pilot lanes | Logistics | Negotiations stall beyond 6 weeks |
| RK-07 | Peak causes outside operational control (e.g. Feb–Mar 2018, unexplained) recur | External | 2 | 2 | 4 | Peak playbook with buffers; daily monitoring; root-cause review after each peak | Logistics | Weekly late rate > 10% outside planned peaks |
| RK-08 | Pilot underpowered or confounded by seasonality | Analytical | 2 | 2 | 4 | 3–4 month phases; avoid straddling peak months; control lanes | BA / Analytics | Confidence interval includes zero at the end of the phase |
| RK-09 | Dashboard numbers do not reconcile after the Power BI build | Delivery | 2 | 2 | 4 | Reconciliation checklist (`dashboard/powerbi/README.md` §5); expected values are tested | BI team | Any measure differs from the checklist |
| RK-10 | T-SQL port behaves differently on SQL Server (only parse-checked) | Technical | 2 | 1 | 2 | Run `sql/tsql` on SQL Server and compare to the DuckDB outputs before production use | BI team | Validation suite reports FAIL on SQL Server |
| RK-11 | Stakeholder needs differ from the hypotheses | Engagement | 2 | 2 | 4 | Week-1 discovery sessions (questions listed in the stakeholder doc) | BA | Sponsor reprioritises after discovery |
| RK-12 | Data licence: the CC BY-NC-SA dataset is used commercially | Legal | 1 | 2 | 2 | Portfolio and educational use only; raw data not redistributed; attribution kept | Author | Any commercial reuse request |

## Top risks (score 6) and response
RK-01 to RK-05 share one pattern: **the analysis is strongest on *where* the problem is and weakest on *how much an intervention will help*.** The plan responds by putting a measured pilot ahead of any scale-up commitment, and by making the scenario assumptions replaceable with measured effects.
