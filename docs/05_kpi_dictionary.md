# KPI dictionary

**Scopes:**
- **W** (window) = purchased 2017-01-01 to 2018-08-31.
- **R** (revenue) = W, excluding canceled/unavailable orders.
- **F** (fulfilment) = W, delivered and with a delivery timestamp.

Each KPI is implemented in SQL, pandas and DAX. The SQL and pandas versions are tested for equality.

| KPI | Definition | Scope | Formula | SQL | Python | DAX | Window value |
|---|---|---|---|---|---|---|---|
| **Late delivery rate** ★ | Share of delivered orders that arrived after the date promised at checkout | F | late orders / delivered orders; late = delivery date > estimated date | q01, q08 | `kpis.kpi_scorecard` | `Late Delivery Rate` | 6.79% |
| On-time delivery rate | 1 − late rate | F | | q01 | ✓ | `On-Time Delivery Rate` | 93.21% |
| **1–2 star review rate** ★ | Share of reviewed orders scoring 1 or 2 | W, reviewed | count(score ≤ 2) / count(reviewed) | q01 | ✓ | `Low Review Rate` | 14.63% |
| Avg review score (delivered) | Mean score of delivered orders | F | | q01 | ✓ | `Avg Review Score (Delivered)` | 4.156 |
| Avg delivery days | Purchase → delivery, mean days | F | | q01 | ✓ | `Avg Delivery Days` | 12.54 |
| Avg promised days | Purchase → estimated date, mean whole days | F | | — | ✓ | `Avg Promised Days` | 24.3 |
| Seller SLA miss rate | Share of delivered orders handed to the carrier after the shipping-limit date | F, handoff known | | q09 | ✓ | `Seller SLA Miss Rate` | 8.92% |
| Excess late orders | Late orders above what the platform late rate predicts for a segment | F | late − delivered × platform rate | `root_cause` | ✓ | `Excess Late Orders` | Top lane SP→RJ: 596 |
| Share of late orders, post-handoff | Late orders whose seller handed over on time | F, single seller | | — | `root_cause` | `Late Orders - Post-Handoff Delay` | 72.3% |
| Stage medians | Median approval hours; approval→carrier days; carrier→customer days | F, excluding dq-flagged | | q08 | — | `Median ...` | 0.34 h; 1.84 d; 7.12 d |
| Revenue orders | Count of revenue orders | R | | q01 | ✓ | `Revenue Orders` | 97,910 |
| Product revenue | Σ item price (excludes freight), BRL | R | | q01, q02 | ✓ | `Product Revenue` | R$13,449,529.68 |
| Average order value | Product revenue / revenue orders | R | | q01 | ✓ | `Average Order Value` | R$137.37 |
| Freight-to-price ratio | Σ freight / Σ item price | R | | q01, q18 | ✓ | — | 16.61% |
| Repeat customer share | Customers with ≥ 2 revenue orders / all customers | R | by `customer_unique_id` | q12 | `kpis.repeat_rate` | — | 3.04% |
| Cancel / unavailable rate | Share of window orders canceled or unavailable | W | | q01 | ✓ | — | 1.19% |

★ = primary KPIs for the engagement. Targets are in `01_project_charter.md` §5.

## Seller tier rule (dashboard and action list)
Sellers with fewer than 30 delivered orders in the window → *Low volume*. Of the rest:
- *Intervene* if SLA-miss rate > 15% **and** late rate > 10%;
- *Monitor* if either condition holds;
- otherwise *Healthy*.

The thresholds are judgement calls, set at roughly 1.5–2× the platform averages (8.9% SLA miss, 6.8% late). Revisit them with the Seller Success team.

## Known metric caveats
- "Late" is measured against the platform's own promise. A long but on-time delivery is not late, and a longer promise lowers the late rate. That is why *avg promised days* is a guardrail.
- Root-cause and scenario figures use **single-seller** delivered orders (98.7% of delivered orders), so seller and lane attribution is unambiguous. Dashboard measures use all delivered orders, so platform rates can differ slightly (6.87% vs. 6.79%).
