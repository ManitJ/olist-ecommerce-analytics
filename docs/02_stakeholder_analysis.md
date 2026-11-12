# Stakeholder analysis (hypothetical)

> All stakeholders below are **hypothetical roles** typical of a marketplace operator. No interviews took place. The "needs" are **hypotheses to validate** in discovery sessions. They are not findings. The "evidence available" column shows what this dataset can and cannot give each stakeholder.

## Stakeholder map

| Stakeholder | Role in decision | Influence | Interest | Hypothesised needs | Evidence this project provides | Gaps |
|---|---|---|---|---|---|---|
| **VP Operations** (sponsor) | Funds and approves interventions | High | High | One page: where to act first, expected range of impact, how progress is tracked | Executive memo, scenario model, dashboard page 1 | Cost of interventions (not in data) |
| **Head of Logistics / Carrier Management** | Owns carrier contracts and lane SLAs | High | High | Which lanes and months fail; evidence to take into carrier negotiations | Lane excess ranking, monthly stage medians, peak decomposition | **No carrier ID** in the data, so lanes cannot be attributed to a named carrier |
| **Seller Success lead** | Owns seller performance programmes | Medium | High | Which sellers miss shipping deadlines, and the impact of those misses | Seller scorecard and tiers, SLA-miss impact | Seller capacity / stock data |
| **Customer Experience (CX) lead** | Owns reviews, contacts, refunds | Medium | High | How much lateness drives bad reviews; how much is avoidable | Controlled review-gap estimates, dose-response | Contact-centre and refund data |
| **Marketplace Product Manager** | Owns the checkout delivery-date promise | Medium | Medium | Whether the promise algorithm should change | Out-of-sample promise backtest | Conversion data (effect of the promise on purchase) |
| **Finance / FP&A** | Challenges the business case | High | Medium | Quantified impact; no unsupported ROI | Order-level impact ranges; explicit statement that no ROI is computed | Cost, margin, customer lifetime value |
| **BI / Data team** | Builds and maintains the dashboard | Low | Medium | Clear model, measure definitions, tests | Star schema, DAX, Power Query, reconciliation checklist | Production refresh pipeline |
| Sellers (external) | Affected by SLA enforcement | Medium | High | Fair, transparent rules; time to comply | Tier rules based on ≥ 30 orders, documented thresholds | — |
| Carriers (external) | Affected by lane reviews | High | Medium | Specific, verifiable performance data | Lane-level late rates with order counts | Carrier tracking events |

## Influence / interest grid
```
             LOW INTEREST                       HIGH INTEREST
HIGH    | Finance / FP&A        (keep satisfied) | VP Operations, Head of Logistics,   |
INFLU.  | Carriers                              |  (manage closely)                    |
        +---------------------------------------+-------------------------------------+
LOW     | BI / Data team        (monitor)       | Seller Success, CX, Product,        |
INFLU.  |                                       |  Sellers (keep informed / involve)  |
```

## RACI for the recommended programme
| Activity | VP Ops | Logistics | Seller Success | CX | Product | Finance | BI |
|---|---|---|---|---|---|---|---|
| Approve priorities & targets | **A** | C | C | C | C | C | I |
| Lane recovery pilot (R1) | A | **R** | I | C | I | C | C |
| Peak-season playbook (R2) | A | **R** | R | C | C | I | C |
| Seller SLA programme (R3) | A | C | **R** | I | C | I | C |
| KPI dashboard & weekly review (R4) | A | C | C | C | I | I | **R** |
| Carrier/tracking data capture (R5) | A | **R** | I | I | C | I | R |

R = Responsible, A = Accountable, C = Consulted, I = Informed.

## Discovery questions to validate in week 1
1. Logistics: Which carriers serve SP→RJ and SP→BA? Are lane-level SLAs already in the contracts?
2. Logistics: What happened in Feb–Mar 2018? (Carrier transit time rose sharply. The data alone cannot say why.)
3. Seller Success: How is `shipping_limit_date` communicated to sellers, and are sellers alerted before it passes?
4. Product: How is the checkout estimate calculated today? (The backtest suggests it already behaves roughly like a route-level percentile.)
5. Finance: What are the cost of a 1–2 star review (refunds, contacts) and the value of a retained customer? These are needed to turn the order-level impacts into money.
