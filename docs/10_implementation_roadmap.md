# Implementation roadmap

> A proposed plan for a hypothetical sponsor. Durations are planning estimates, not measured outcomes.

## Phases

| Phase | Weeks | Workstreams | Exit criteria |
|---|---|---|---|
| **0. Mobilise** | 1–2 | Validate stakeholder hypotheses; confirm targets (charter §5); assign a single owner for promise reliability (R4) | Signed-off targets; owner named; discovery questions answered (stakeholder doc) |
| **1. Quick wins & foundations** | 2–8 | R4 dashboard live with weekly review · R3 seller alerts plus outreach to 57 "Intervene" sellers · R5 carrier ID capture specified and built | Weekly review running for 4 weeks; alerts live; carrier ID on ≥ 95% of new orders |
| **2. Lane pilot** | 6–22 | R1 staggered lane rollout: phase A on SP→RJ and SP→ES (3–4 months); controls PR→RJ and SP→BA; then extend to controls | Difference-in-differences estimate of the lane effect, with confidence interval; go/no-go to scale |
| **3. Peak readiness** | Starts 10 weeks before Nov | R2 capacity commitments; earlier cut-offs; temporary buffer on flagged lanes; daily peak monitoring | Peak-month late rate ≤ 10% |
| **4. Scale & re-baseline** | After pilot | Extend R1 to all anomalous lanes; replace scenario assumptions with measured effects; reset targets | Late rate ≤ 6% (2 quarters), ≤ 5% (12 months) |

```mermaid
gantt
    dateFormat  YYYY-MM-DD
    axisFormat  W%W
    section Foundations
    Mobilise & targets (R4 owner)     :a1, 2026-01-05, 14d
    KPI dashboard + weekly review (R4):a2, after a1, 21d
    Carrier ID capture (R5)           :a3, after a1, 42d
    section Sellers
    Alerts + Intervene-tier plans (R3):b1, after a1, 42d
    section Lanes
    Pilot phase A: SP-RJ, SP-ES (R1)  :c1, after a3, 105d
    Phase B: control lanes join       :c2, after c1, 60d
    section Peak
    Peak readiness (R2)               :d1, 2026-09-01, 60d
```
*The Gantt dates are illustrative. They show sequencing, not a commitment.*

## Dependencies
| ID | Dependency | Affects | Mitigation |
|---|---|---|---|
| D1 | Carrier ID per order (R5) | R1 carrier-specific SLAs | Start R1 with lane-level reviews involving all carriers serving the lane |
| D2 | Logistics owns carrier contracts and can renegotiate lane terms | R1, R2 | Sponsor (VP Ops) sponsorship; early involvement in discovery |
| D3 | Seller communication channel exists for alerts | R3 | Fall back to email / seller-portal banner |
| D4 | Power BI Desktop and a refresh pipeline | R4 | Streamlit preview available in the meantime |
| D5 | Finance inputs (cost of a bad review, intervention costs) | Business case in money terms | Present operational outcomes only until provided |

## Assumptions
- The 2017–2018 patterns still hold. **Rerun the pipeline on current data in Phase 0** before committing.
- Lane anomalies stem from operational causes that a carrier or last-mile change can address. This is untested (hypothesis in F3).
- Sellers respond to alerts and plans. The size of the response is unknown (L2 assumptions).

## Governance and measurement
- **Weekly:** lane and seller scorecards (dashboard pages 1–3), with actions logged.
- **Monthly:** KPI vs. target, including guardrails (average promised days, volume).
- **End of pilot:** the measured effect replaces the L1 scenario assumption, and the business case is re-run.
