# Project audit

Status legend: ✅ complete and verified · 🟡 complete but not fully verifiable here · ❌ not delivered (with reason)

## 1. Deliverables checklist

### Data
| Deliverable | Status | Verification |
|---|---|---|
| Public dataset with traceable source and licence | ✅ | Olist v2, CC BY-NC-SA 4.0 (licence read from the Kaggle API); `data/README.md` |
| Reproducible download | ✅ | `make data`; SHA-256 manifest; clean-room rebuild downloaded identical files |
| Profiling: missing values, duplicates, types, referential integrity, outliers, inconsistent values | ✅ | `docs/04_data_cleaning_log.md` (14 documented decisions) |
| Raw data preserved; cleaning documented and reproducible | ✅ | `stg` layer kept as text; rules implemented twice and tested for equality |
| Profitability limitation documented | ✅ | No cost/margin data in the dataset, so no profit or ROI anywhere |

### SQL
| Deliverable | Status | Verification |
|---|---|---|
| Relational schema with PK/FK | ✅ | `sql/schema.sql`. Constraints are enforced by DuckDB on load (0 rejected rows). |
| Load and cleaning scripts | ✅ | `sql/load.sql` |
| ≥ 15 substantive analytical queries | ✅ | 20 named queries in `sql/analysis.sql`, each with its business question (`tests/test_sql.py`) |
| KPIs with definitions | ✅ | `docs/05_kpi_dictionary.md` |
| Validation and reconciliation queries | ✅ | `sql/validation.sql`: 31 PASS / 0 FAIL / 9 INFO |
| Data dictionary | ✅ | `sql/data_dictionary.md` |
| Runs against the actual dataset | ✅ | `make pipeline` |
| SQL Server 2022 scripts | 🟡 | `sql/tsql/` is generated and parse-checked as T-SQL, **but not executed on SQL Server** (none available) |

### Python
| Deliverable | Status | Verification |
|---|---|---|
| Reusable modules: ingestion, cleaning, validation, EDA, KPIs | ✅ | `python/olist_ba/` (13 modules) |
| Business-question charts | ✅ | 17 charts in `assets/charts/`, all inspected after rendering |
| Statistical methods where useful | ✅ | Mann-Whitney, chi-square, Wilson CIs, Spearman, logistic regression with seller-clustered SEs, within-seller stratification, direct standardisation, out-of-sample backtest, power calculation |
| `requirements.txt` | ✅ | Pinned versions; clean-room install succeeded |
| Tests for transformation and KPI logic | ✅ | See §3 |
| Executed notebook with explanations | ✅ | `python/notebooks/analysis.ipynb` (0 errors; runs on the project venv) |

### Power BI
| Deliverable | Status | Verification |
|---|---|---|
| Star schema / semantic model | ✅ | `data/bi/` (generated), `dashboard/powerbi/model.md`; key and FK integrity tested |
| DAX measures, documented | 🟡 | `measures.dax`. The logic mirrors the tested SQL/Python, and the scenario formula is replicated in a test. **Not executed in Power BI.** |
| Power Query steps | 🟡 | `power_query.m`, generated from the real schemas. Not executed in Power BI. |
| Dashboard build guide and page spec | ✅ | `dashboard/powerbi/README.md`, `dashboard_spec.md` |
| Editable `.pbix` / `.pbip` | 🟡 | `.pbix` built (Executive Overview page; `screenshots/OList_Dashboard.png`). Not published yet: it embeds imported data, pending licence review. |
| Interactive preview (clearly labelled) | ✅ | Streamlit app; runs headless in tests and reproduces the KPIs; 4 real screenshots |

### Business analysis
| Deliverable | Status | Location |
|---|---|---|
| Problem statement and project charter | ✅ | `docs/01_project_charter.md` |
| Stakeholder map (hypothetical) | ✅ | `docs/02_stakeholder_analysis.md` |
| BRD with functional and non-functional requirements | ✅ | `docs/03_business_requirements.md` |
| KPI dictionary | ✅ | `docs/05_kpi_dictionary.md` |
| Current- and future-state process maps | ✅ | `docs/07_process_improvement_proposal.md` (Mermaid) |
| ≥ 5 evidence-backed insights | ✅ | 8 findings with evidence grades, `docs/06_insights_and_evidence.md` |
| Impact-vs-effort recommendations | ✅ | `docs/09_recommendations.md` |
| Scenario analysis with transparent assumptions | ✅ | `docs/08_scenario_analysis.md`; sensitivity and robustness variant |
| Roadmap, risks, assumptions, dependencies | ✅ | `docs/10_implementation_roadmap.md`, `docs/11_risk_register.md` |
| Executive summary and recommendation memo | ✅ | `reports/` |
| Interview walkthrough | ✅ | `docs/12_interview_walkthrough.md` |
| Hiring-manager critique and fixes | ✅ | `docs/13_hiring_manager_review.md` |

### Repository
| Deliverable | Status | Note |
|---|---|---|
| README, LICENSE, .gitignore, data README | ✅ | The LICENSE has a `[YOUR NAME]` placeholder to fill in |
| LinkedIn draft | ✅ | Kept outside the public repo (not published) |
| Git repository / GitHub publication | ❌ | Not initialised or published. Awaiting the author's approval (see §5). |

## 2. Reproducibility evidence
- **Clean-room rebuild.** The repo was copied without `.venv`, data or outputs, then `make setup && make all` was run. Result: dataset downloaded, pipeline and notebook ran, and **all 42 output files, all 8 BI tables and all 17 charts were byte-identical** to the committed versions. The raw files matched the original SHA-256 hashes.
- **Bug found by the clean room and fixed:** HTTPS certificate failure on python.org's macOS Python. The fix uses `certifi`, now pinned.

## 3. Tests
`make test` runs pytest over `tests/`:

| Suite | What it proves |
|---|---|
| `test_clean.py`, `test_kpis.py`, `test_stats.py` | Cleaning rules, KPI definitions, bucket boundaries and statistical helpers on hand-built fixtures |
| `test_reconciliation.py` | Validation suite passes; **SQL = pandas** on 29 columns × 99,441 orders; headline, monthly, bucket, frequency and cohort KPIs match |
| `test_sql.py` | ≥ 15 queries, required SQL techniques, no positional references, T-SQL parses, window functions deterministic |
| `test_scenarios.py` | Attributable-share logic on a toy example; **DAX formula replication = Python scenario**; overlap and monotonicity |
| `test_bi_export.py` | Dimension keys unique; every fact FK resolves; Power Query columns match the CSVs |
| `test_dashboard_preview.py` | The Streamlit preview runs without exceptions and shows reconciled KPI values |
| `test_docs_numbers.py` | Headline numbers in the README, memo, summary and insights match `outputs/key_metrics.json` |
| `test_repo_links.py` | Every file path and markdown link in the docs and code exists |

The final run result is recorded in §7.

## 4. Exact commands
```bash
make setup         # python3 -m venv .venv; pip install -r requirements.txt; register venv kernel
make data          # download + verify the dataset into data/raw/
make pipeline      # SQL build/validation/analysis → pandas → stats → root cause → scenarios → charts → BI → T-SQL → key metrics
make notebook      # execute python/notebooks/analysis.ipynb in place
make test          # all tests
make preview       # Streamlit dashboard preview on http://localhost:8501
make all           # data + pipeline + notebook + test
```

## 5. Publishing to GitHub (when you approve)
```bash
cd olist-ecommerce-analytics
# 1. Replace [YOUR NAME] in LICENSE
git init -b main
git add . && git status         # confirm: no data/raw CSVs, no .venv, no .duckdb or parquet files
git commit -m "Delivery performance & customer satisfaction case study"
gh repo create <repo-name> --public --source . --push   # or create the repo on github.com and push
```
Afterwards, add the repo URL to the LinkedIn draft. Optionally pin the repo on your GitHub profile.

## 6. Study guide: what to learn before claiming proficiency
Prioritised by how likely an interviewer is to probe it and how central it is to this project:

1. **Correlation vs. causation and confounding.** Why within-seller comparison controls for stable seller traits; what an unobserved order-level confounder is; why dose-response supports but does not prove causation. *Be able to explain F6 without notes.*
2. **Experiment and pilot design.** Difference-in-differences, staggered rollouts, control groups, statistical power and minimum detectable effect, seasonality confounds.
3. **SQL window functions.** `LAG`, running totals with frame clauses, `NTILE`, `RANK` vs `DENSE_RANK` vs `ROW_NUMBER`, and why tie-breakers matter. Rewrite q02, q04 and q14 from memory.
4. **Logistic regression interpretation.** Odds ratio vs. average marginal effect, discrete vs. continuous marginal effects, and why standard errors are clustered.
5. **Data modelling.** Star schema, grain, fact vs. dimension, why `fact_orders` and `fact_order_items` are kept separate, and the role of a date table.
6. **DAX fundamentals.** `CALCULATE` and filter context, `REMOVEFILTERS`, iterators (`SUMX`), what-if parameters. Then **build the actual Power BI report** from the package.
7. **Scenario modelling.** Attributable share, overlap removal (1 − Π(1 − p)), sensitivity analysis, and why you don't sum lever effects or invent ROI.
8. **Standardisation.** Direct standardisation, and why comparing SP→RJ to distance-matched lanes is fairer than comparing it to the average.
9. **BA artefacts.** BRD structure, traceability, RACI, impact/effort prioritisation, risk scoring. Be ready to defend each prioritisation call.
10. **Data quality practice.** Reconciliation, flag-vs-delete decisions, and the difference between grain errors and value errors.
11. **T-SQL differences from DuckDB.** `DATETRUNC`, `PERCENTILE_CONT` as a window function, NULL ordering, `GO` batches, `BULK INSERT`. Then run `sql/tsql` on a real SQL Server.
12. **Reproducibility engineering.** Virtual environments, pinned dependencies, kernels, deterministic outputs, and why the clean-room test matters.

## 7. Final test run
Recorded after the last code change (`make test`, Python 3.13.1, macOS arm64):

**317 passed, 0 failed, 0 skipped.** The 317 break down into **79 functional and data tests** and **238 automated link/path checks**:

| Suite | Tests |
|---|---|
| test_bi_export | 15 |
| test_clean | 9 |
| test_dashboard_preview | 1 |
| test_docs_numbers | 18 |
| test_kpis | 15 |
| test_reconciliation | 8 (each covers the full 99,441-order dataset) |
| test_scenarios | 5 |
| test_sql | 5 |
| test_stats | 3 |
| test_repo_links | 238 (one per referenced path) |

The same suite also passed in the clean-room rebuild (§2). At that point there were 3 expected failures, for links to this audit file before it was written.
