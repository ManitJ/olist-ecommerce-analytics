# Self-review from a hiring manager's perspective

Before finalising, the project was reviewed as an analytics or consulting hiring manager would review it (Big Four, systems integrator, or a bank's analytics team). The question was: *what would make me doubt this candidate's judgement or rigour?*

Below are the issues found **during this build**, what was changed, and what still stands as a known weakness.

## A. Issues found and fixed

| # | Critique | Why it matters to a hiring manager | Fix applied | Evidence |
|---|---|---|---|---|
| 1 | The first version read like a generic Kaggle tour: revenue, categories, RFM, payment mix | Signals "tool user", not "business analyst" | Re-framed around **one decision** with a sponsor, success criteria, guardrails and a staged target. Commercial charts moved to an appendix. | `01_project_charter.md`, README structure |
| 2 | Percent tick labels were rounded (2.5% shown as "2%") | Misleading axes are a credibility red flag | Explicit tick spacing; every chart re-inspected after rendering | `charts.py` (`MultipleLocator`) |
| 3 | The promise-backtest chart title claimed "far fewer broken promises" | The current estimate sits *on* the trade-off curve, so the title overclaimed | Added an equal-promise comparison (7.45% vs. 7.83%); title now says "trade-off, not a free win"; recommendation **deprioritised** | F7, chart 16 |
| 4 | The logistic regression marginal effect treated the binary `is_late` as continuous | Reported 25 pp instead of the correct 51 pp: a real statistical error | `get_margeff(dummy=True)` (discrete 0→1 change) | `root_cause.py` |
| 5 | Regression standard errors assumed independent orders | Orders cluster within sellers, so the CI was too narrow | Seller-clustered standard errors (CI 49.6–52.5 pp) | `root_cause.py` |
| 6 | "Worst lanes" were selected and measured on the same data | Risk of regression to the mean | Persistence test, 2017 → 2018: ρ = 0.68; SP→RJ 2.2× then 2.0× the platform rate | `lane_persistence.csv` |
| 7 | "RJ is late" could simply mean "RJ is far" | Recommending a carrier fix for a geography problem would be wrong | Distance-matched standardisation: SP→RJ is 2.7× its expectation, while SP→CE is 1.0× | `lane_distance_matched.csv`, chart 17 |
| 8 | Peak months were identified with hindsight, which flattered the peak lever | Overstated scenario impact | November-only variant: base case 6.1% instead of 5.3%. Targets restated. | `scenario_variant_november_only.csv` |
| 9 | Scenario: low-review avoidance was scaled incorrectly | Wrong number in an executive deliverable | Formula corrected; DAX replication tested | `scenarios.py`, `test_scenarios.py` |
| 10 | SQL window functions with ties (`NTILE`, `ROW_NUMBER`) gave different results on each run | Non-reproducible numbers | Deterministic tie-breakers plus a regression test | `test_sql.py` |
| 11 | The notebook was silently executing on Anaconda's Python, not the project environment | "Reproducible" would have been untrue | Venv kernel registered; `python -m nbconvert`; the notebook prints its interpreter | `Makefile`, notebook cell 1 |
| 12 | The pilot power calculation used the wrong monthly volume (670 instead of 507) | Pilot sizing must be right | Recomputed with statsmodels; phase length set to 3–4 months | `08_scenario_analysis.md` §6 |
| 13 | Docs referenced files that had been renamed | Broken links read as careless | Automated link test across all docs and code | `test_repo_links.py` |
| 14 | Temptation to ship a hand-written `.pbip` or a mockup as "the dashboard" | Claiming an unvalidated deliverable is worse than not having it | Honest build package plus a *labelled* Streamlit preview, with real screenshots | `dashboard/` |

## B. Known weaknesses that remain (and how to address them)

| Weakness | Severity | Why it was not fixed | Next step |
|---|---|---|---|
| No `.pbix` / `.pbip` file | High for BI-heavy roles | Power BI Desktop is Windows-only | Build it on Windows following `dashboard/powerbi/README.md` (1–2 h), commit it as PBIP, add screenshots |
| T-SQL never executed on SQL Server | Medium | No instance available | Run `sql/tsql` in Docker or Azure SQL and compare outputs |
| Lanes are at state level | Medium | State → state keeps sample sizes adequate | Repeat at city or zip-prefix level for SP→RJ to localise the problem |
| Scenario assumptions are judgement | Medium (mitigated) | No intervention data exists | Ranges, sensitivity analysis and a pilot design that replaces them |
| Seller tier thresholds are judgement | Low | No policy reference | Calibrate with Seller Success; test the sensitivity of tier counts |
| No cost or margin data, so no money | Inherent | Not in the dataset | Finance inputs (DR-3) |
| Data is from 2016–2018 | Inherent | Public dataset | The pipeline is rerunnable on current data |
| Stakeholders are hypothetical | Inherent to a portfolio project | — | Labelled throughout; discovery questions provided |

## C. What a reviewer should be able to verify in 10 minutes
1. `make test` passes: unit tests, plus integration tests proving SQL and pandas give identical results.
2. Every number in `reports/executive_memo.md` appears in `outputs/key_metrics.json` or a named output file.
3. Every finding in `06_insights_and_evidence.md` carries an evidence grade and a limitation.
4. Nothing claims a result that was not produced. The missing Power BI file and the unexecuted T-SQL are stated in the README.
