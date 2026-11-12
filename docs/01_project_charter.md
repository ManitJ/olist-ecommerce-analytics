# Project charter: Delivery Performance & Customer Satisfaction

> **Engagement framing.** This is a portfolio case study built on a real public dataset (Olist, Brazil, 2016–2018). The business scenario, the stakeholders and the targets are **hypothetical**. They were constructed the way a Business Analyst would frame a real engagement. No stakeholder interviews took place, and no interventions were implemented. Every number cited comes from the reproducible pipeline (`outputs/key_metrics.json`).

## 1. Decision to be made
**How should the marketplace prioritise operational improvements to reduce delivery delays and improve customer satisfaction?**

The sponsor needs to choose which two or three interventions to fund next quarter. To do that, they need to know where late deliveries originate, how much they matter to customers, and what each intervention could plausibly achieve.

## 2. Problem statement
In the 20 months from January 2017 to August 2018:
- **6.8%** of delivered orders arrived after the delivery date promised at checkout (6,531 of 96,203).
- The share of reviews scoring 1–2 stars was **14.6%**.
- Late orders received a 1–2 star review **62%** of the time, against **9%** for on-time orders.
- Customers rarely return (97% bought once), so reviews are the platform's main reputation signal to *new* buyers.
- Revenue growth slowed through 2018: year-on-year growth fell from +687% in January to +49% in August. That makes conversion of new buyers increasingly important.

## 3. Objectives
1. **Diagnose:** locate where in the fulfilment chain late deliveries originate (seller vs. post-handoff), and where (lanes, sellers) and when (seasonality) they concentrate.
2. **Validate:** test whether the lateness–satisfaction link survives controls, and say clearly what is proven and what is only associated.
3. **Prioritise:** rank interventions by evidence-backed impact against effort.
4. **Size:** estimate the plausible range of each intervention's impact, with transparent, adjustable assumptions.
5. **Monitor:** specify the KPI dashboard and targets used to track whether the interventions work.

## 4. Scope
| In scope | Out of scope |
|---|---|
| Delivered orders, Jan 2017 – Aug 2018 (20 complete months) | Sparse 2016 data and the truncated Sep–Oct 2018 data (shown in validation, excluded from trends) |
| Fulfilment stages visible in the data: purchase, approval, seller handoff, customer delivery | Carrier-level analysis: the dataset has **no carrier identifier** (logged as data requirement DR-1) |
| Reviews (scores, plus whether a comment was written) | Free-text sentiment / NLP on Portuguese comments |
| Revenue as context | **Profitability.** The dataset has no product cost or margin, so no profit or ROI figures are produced |

## 5. Success criteria (proposed)
Targets are proposals for the sponsor to ratify. They are set from the scenario analysis (`docs/08_scenario_analysis.md`), not from industry benchmarks.

| KPI | Baseline (source) | Target | Rationale |
|---|---|---|---|
| **Late delivery rate** (primary) | 7.9% in the baseline year Sep-17 to Aug-18 (6.8% over the full window) | **≤ 6.0%** within 2 quarters of rollout; **≤ 5.0%** within 12 months (stretch) | The scenario base case reaches 5.3%, or 6.1% if only November peaks are addressable. ≤ 6% is achievable at about base execution. 5% needs high-case execution or a pilot that beats the assumptions. A staged target avoids committing to an outcome the evidence does not yet support. |
| 1–2 star review rate (secondary) | 12.9% in the baseline year | ≤ 11.6% | Scenario base case. Treat it as an expectation, not a commitment: causality is not proven. |
| SP→RJ lane late rate | 14.3% | ≤ 10.5% | Removing half of the lane's excess above the platform rate (L1 base assumption) |
| Seller SLA miss rate | 8.9% of delivered orders | ≤ 6.0% | A conservative version of the L2 base assumption |
| Peak-month late rate | 15.3% in the 3 peak months of the baseline year | ≤ 10% | L4 base assumption |
| **Guardrails** (must not worsen) | Avg promised days 24.3; order volume; freight-to-price ratio 16.6% | No increase > 1 day; no volume decline attributable to the changes | Stops the late rate being "improved" just by inflating promises or by losing sellers |

## 6. Deliverables
| Deliverable | Location |
|---|---|
| Validated data model, SQL analysis (20 queries), validation suite | `sql/` |
| Python pipeline, statistics, root-cause analysis, scenario model, tests | `python/`, `tests/` |
| Power BI build package plus interactive preview | `dashboard/` |
| BRD, process improvement proposal, risk register, roadmap | `docs/` |
| Executive memo and executive summary | `reports/` |

## 7. Constraints and assumptions
- **Observational data only.** No interventions were run, so causal claims are limited. Effects should be confirmed by a controlled pilot.
- **Historical data from 2016–2018.** Patterns may have shifted since then. Rerun the pipeline on current data before acting.
- **Single analyst; no stakeholder access.** Stakeholder needs in `02_stakeholder_analysis.md` are inferred hypotheses. Validating them is a first-week activity in a real engagement.
