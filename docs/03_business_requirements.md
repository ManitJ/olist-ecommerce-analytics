# Business Requirements Document (BRD)

**Initiative:** Delivery performance monitoring and improvement programme
**Version:** 1.0 (portfolio case study, hypothetical sponsor; see `01_project_charter.md`)
**Status:** Draft for sponsor review

## 1. Business context
The marketplace promises a delivery date at checkout. 6.8% of delivered orders miss it. Missed promises are associated with a large rise in 1–2 star reviews (raw gap 53.7 pp; 51.1 pp after controls). Operations leadership has no shared, trusted view of where delays originate. Without one, it cannot prioritise interventions or tell whether they are working.

## 2. Business requirements (BR)
| ID | Requirement | Priority | Rationale (evidence) |
|---|---|---|---|
| BR-1 | Leadership can see the late-delivery rate against target, monthly, at platform, region, state, lane and seller level | Must | Lateness is concentrated by lane and month (`insights` F2–F4) |
| BR-2 | Each late order is classified by where the delay began (seller handoff vs. after carrier handoff) | Must | 72% vs. 28% split drives different owners (F2) |
| BR-3 | Lanes and sellers are ranked by **excess** late orders (above the platform rate), not by raw counts | Must | Raw counts favour big sellers and lanes. Excess shows where intervention removes the most late orders (F3) |
| BR-4 | Operations can model the effect of interventions under adjustable assumptions | Should | Supports funding decisions (`08_scenario_analysis.md`) |
| BR-5 | Customer-impact metrics (1–2 star rate) are shown alongside delivery metrics | Must | Delivery KPIs alone do not show what customers experience |
| BR-6 | Guardrail metrics (promised days, order volume) are shown with the target KPIs | Must | Stops the late rate being "improved" by inflating promises |
| BR-7 | Carrier identity and tracking events are captured per order | Should | Needed to attribute post-handoff delay (DR-1) |

## 3. Functional requirements (FR)
| ID | Requirement | Traces to | Acceptance criteria |
|---|---|---|---|
| FR-1 | Dashboard shows KPI cards: late rate (with status text against a 5% target), 1–2 star rate, average delivery days vs. promised, seller SLA-miss rate, revenue | BR-1, BR-5, BR-6 | With no filters, the values equal the reconciliation table in `dashboard/powerbi/README.md` §5 |
| FR-2 | Monthly late-rate trend with a target line; the 3 peak months are identifiable | BR-1 | Trend matches `q08_fulfilment_stage_trend.late_rate` |
| FR-3 | Late orders are split into "seller missed shipping limit" and "delay after carrier handoff" | BR-2 | Shares match `outputs/root_cause/late_decomposition.csv` |
| FR-4 | Lane table ranked by excess late orders, with order counts shown beside every rate | BR-3 | Top lane = SP→RJ. Lanes with fewer than 30 orders are excluded |
| FR-5 | Seller table with tier (Intervene / Monitor / Healthy / Low volume) using the documented rule | BR-3 | Tier counts match `dim_seller.seller_tier` |
| FR-6 | Drill down Region → State and Year → Month; drill through from a lane to its sellers | BR-1 | Manual test checklist in `dashboard_spec.md` |
| FR-7 | Scenario page with four what-if sliders (L1, L2, L4, review gap). Shows baseline vs. scenario late rate and orders avoided | BR-4 | Default sliders reproduce 1,843 orders avoided and 5.34% (tested in `tests/test_scenarios.py`) |
| FR-8 | Global slicers: year-month range and region, synced across pages | BR-1 | Slicer changes update every page except the scenario page, which has a fixed baseline by design |

## 4. Non-functional requirements (NFR)
| ID | Category | Requirement | How it is met |
|---|---|---|---|
| NFR-1 | Accuracy | Every KPI reconciles to the source data | 31 validation checks (`sql/validation.sql`); SQL vs. pandas parity on all 29 order-level columns (`tests/test_reconciliation.py`) |
| NFR-2 | Reproducibility | A clean environment rebuilds every output with one command | `make setup && make all`; pinned `requirements.txt`; deterministic tie-breaks in window functions (regression-tested) |
| NFR-3 | Transparency | Every metric has a written definition, scope and source query | `05_kpi_dictionary.md`, `sql/data_dictionary.md` |
| NFR-4 | Performance | Full pipeline under 2 minutes on a laptop | ~31 s measured |
| NFR-5 | Accessibility | Status is never shown by colour alone; every rate shows its order count; alt text on visuals | `dashboard_spec.md` checklist |
| NFR-6 | Portability | Target engine SQL Server 2022 | T-SQL port in `sql/tsql/`, parse-checked. **Execution on SQL Server not yet verified.** |
| NFR-7 | Data licensing | Raw data is not redistributed; attribution kept | `.gitignore`, `data/README.md`, `LICENSE` scope note |
| NFR-8 | Privacy | No personal data beyond hashed IDs and zip prefixes | Source is anonymised. Review text is reduced to has/has-not flags |

## 5. Data requirements
| ID | Requirement | Status |
|---|---|---|
| DR-1 | **Carrier identifier per order** | **Not available.** Blocks carrier-level attribution of the 72% post-handoff delay. Request from Logistics. |
| DR-2 | Carrier tracking events (pickup, hub, out-for-delivery) | Not available. Would split transit time from last-mile time. |
| DR-3 | Intervention cost and margin data | Not available. Blocks ROI. No ROI is claimed. |
| DR-4 | Conversion by promised delivery days | Not available. Blocks sizing the commercial effect of changing promises. |
| DR-5 | Daily refresh of orders, items, reviews | The design supports it (idempotent rebuild). Not implemented: static dataset. |

## 6. Assumptions and dependencies
- A1. The order-level `order_estimated_delivery_date` is the date shown to the customer at checkout. (This is the Olist field definition. Not independently verified.)
- A2. `shipping_limit_date` is the seller's handoff deadline. Handoff time is approximated by `order_delivered_carrier_date`.
- A3. Each order's seller, lane and category are those of its highest-priced item. 98.7% of delivered orders have a single seller.
- D1. Carrier data (DR-1) is needed before the lane programme can set carrier-specific SLAs.
- D2. Power BI Desktop (Windows) is needed to build the report from the package. See `dashboard/powerbi/README.md`.

## 7. Traceability summary
BR-1 → FR-1, FR-2, FR-6, FR-8 · BR-2 → FR-3 · BR-3 → FR-4, FR-5 · BR-4 → FR-7 · BR-5 → FR-1 · BR-6 → FR-1 · BR-7 → DR-1, DR-2.
