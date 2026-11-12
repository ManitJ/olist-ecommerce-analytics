# SQL

| File | Purpose |
|---|---|
| `schema.sql` | Two-layer schema: `stg` (raw text) and `dw` (typed, PK/FK/CHECK constraints enforced) |
| `load.sql` | Loads the CSVs into `stg`, then cleans into `dw`; creates the views `dw.v_order_review` and `dw.v_order_summary` |
| `validation.sql` | 8 validation suites (40 checks: 31 PASS / 9 INFO): row counts, key uniqueness, referential integrity, cent-level reconciliation, business rules, window completeness, data-quality flags |
| `analysis.sql` | 20 named business queries. Each states the question it answers (`-- @question`). |
| `data_dictionary.md` | Tables, columns, derived-field definitions |
| `tsql/` | SQL Server 2022 port (see `tsql/README.md`) |

## Engine choice
**DuckDB** is the development and tested engine:
- It runs in-process from Python with no server.
- It reads the CSVs directly.
- It supports standard SQL: CTEs, window functions, constraints.

SQL Server 2022 was not available on the development machine (macOS, with too little free disk for the SQL Server container). The queries avoid DuckDB-only syntax wherever possible:
- no positional `GROUP BY`;
- 0/1 integer flags instead of booleans in views;
- explicit tie-breakers in `ROW_NUMBER` / `NTILE`.

The code that remains engine-specific (`MEDIAN`, `ISODOW`, `read_csv`) is handled in the T-SQL port.

## Run
```bash
cd python && ../.venv/bin/python -m olist_ba.run_sql     # build + validate + run all analysis queries
```
- Results go to `outputs/sql/analysis/<query>.csv` and `outputs/sql/validation/<suite>.csv`.
- The build fails if any check returns `FAIL`.
- To explore interactively with the DuckDB CLI, run the CLI from the repo root and open `data/processed/olist.duckdb`.

## Query index (`analysis.sql`)
| Query | Business question | Techniques |
|---|---|---|
| q01 | Headline KPI scorecard | CTEs, scalar subqueries, conditional aggregation |
| q02 | Monthly revenue trend | `LAG`, moving average and running total (window frames) |
| q03 | YoY same-period growth | Self-join on month, `UNION ALL` total row |
| q04 | Category Pareto / ABC | `RANK`, cumulative share window, `CASE` classing |
| q05 | Category growth 2018 vs 2017 | Conditional aggregation, `NULLIF` |
| q06 | State performance | Multi-metric aggregation, share-of-total window, `RANK` |
| q07 | Delivery vs. review (dose-response) | `CASE` bucketing in a CTE |
| q08 | Fulfilment stage trend | `MEDIAN` per month, DQ-flag filtering |
| q09 | Seller SLA impact | Share-of-total window |
| q10 | Seller revenue deciles | `NTILE` with deterministic tie-break |
| q11 | Seller risk scorecard | `HAVING`, `DENSE_RANK`, rule-based tiering |
| q12 | Customer purchase frequency | Two-level aggregation |
| q13 | Monthly acquisition cohorts | `DATE_DIFF` month offsets, `COUNT(DISTINCT CASE …)` |
| q14 | First-order lateness vs. repeat | `ROW_NUMBER` + `COUNT() OVER` in one pass |
| q15 | RFM segmentation | Three `NTILE`s, rule-based segments. *Caveat: frequency ≈ 1 for 97% of customers, so this is effectively RM.* |
| q16 | Payment mix | Join + share of value |
| q17 | Instalments vs. AOV | Banding, `MEDIAN` |
| q18 | Freight burden by price band | Banding, ratio of sums (not average of ratios) |
| q19 | Intra- vs. interstate fulfilment | `MIN(CASE …)` to classify multi-seller orders |
| q20 | Weekday × hour demand | `ISODOW`, `EXTRACT` |
