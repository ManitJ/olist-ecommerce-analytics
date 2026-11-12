# Interview walkthrough

A guide to presenting this project in about 5 minutes, then defending each decision under questioning.

## The 60-second story
> "I framed the Olist dataset as a consulting engagement for an operations VP. The decision was: which delivery improvements to fund first. I started with the business problem. About 7% of orders miss their promised date, and those orders get 1–2 star reviews six to seven times as often. With 97% of customers buying once and revenue plateauing, reviews are what new buyers see. Then I asked *where* the lateness comes from. Most of it happens after the seller hands over. It's concentrated in a few lanes and three peak months. SP→RJ alone runs 2.7× the late rate you'd expect for its distance. I tested whether the review link survives controls, it does, and I was explicit that it's still not causal proof. I recommended a lane pilot first, a peak playbook, and a seller alert programme as a quick win. I sized them with a transparent scenario model and set a staged target, because the base case doesn't reach 5%. I also tested one idea that looked attractive, recalibrating delivery promises, and showed out of sample that it doesn't help much. So I recommended against it."

## Decisions and the reasoning behind them

| Decision | What I did | Why | Alternative rejected |
|---|---|---|---|
| Problem framing | One decision question, a hypothetical sponsor, success criteria with guardrails | A BA's value is a decision, not a dataset tour | "Explore the data and report interesting facts" |
| Dataset | Olist: 9 related tables with timestamps for every fulfilment stage | Supports root cause along the process, not just revenue slicing | UCI Online Retail (single table, no delivery data) |
| Analysis window | Jan 2017 – Aug 2018 | 2016 and Sep–Oct 2018 are partial; partial months distort trends | Using all data and getting a false "collapse" in Sep 2018 |
| Customer key | `customer_unique_id`, not `customer_id` | `customer_id` is per order. Using it would make every customer a one-time buyer. | — |
| Two implementations | Cleaning in SQL (DuckDB) **and** pandas, tested for column-level equality | Independent reconciliation catches logic errors that a single implementation hides | Trusting one pipeline |
| Flag, don't delete | 1,359 timestamp anomalies flagged and excluded only where they matter | Deleting rows silently changes KPIs; flags keep the analysis auditable | Dropping "bad" rows |
| Deterministic SQL | Tie-breakers in NTILE / ROW_NUMBER | **I found** RFM results changing between runs. Ties made the output non-reproducible. Now regression-tested. | — |
| "Excess" late orders | Rank lanes and sellers by late orders *above* the platform rate | Raw counts just rank the biggest lanes; excess ranks where intervention removes the most late orders | Ranking by late count or by late rate (rates alone favour tiny lanes) |
| Distance standardisation | Compared each lane with other lanes in the same 50 km bins | Separates "far away" (expected) from "badly served" (actionable). SP→RJ is 2.7× its expectation; SP→CE is 1.0× | Concluding "RJ is far, so it's late" |
| Correlation vs. causation | Raw → within-seller → logistic regression with controls, plus dose-response | Each step removes a class of confounder. The gap barely moves (54 → 53 → 51 pp). | Claiming lateness *causes* bad reviews from a raw comparison |
| Clustered errors | Seller-clustered standard errors in the regression | Orders from the same seller are not independent; naive errors overstate precision (CI widened from 49.8–52.4 to 49.6–52.5) | Default i.i.d. standard errors |
| Selection-bias check | Tested whether 2017's worst lanes were still bad in 2018 | Lanes picked *because* they were bad can regress to the mean. Persistence (ρ = 0.68; SP→RJ 2.2× then 2.0×) shows it's structural. | Trusting a same-sample ranking |
| Hindsight check on peaks | Scenario variant with the peak lever on November only | Feb–Mar 2018 was chosen ex post. Only Black Friday is predictable, so the base case drops to about 6.1%. | Presenting only the flattering version |
| Marginal effect, not odds ratio | Reported the average marginal effect (pp) alongside the OR | An odds ratio of 17 sounds dramatic and isn't intuitive; 51 percentage points is what a manager can use. I also caught that statsmodels treated the binary variable as continuous, and fixed it (`dummy=True`). | Leading with "17× the odds" |
| Backtest out of sample | Calibrated promises on 2017, tested on 2018 | In-sample calibration always looks good. Out of sample it showed the idea does not work. | Recommending promise changes on in-sample results |
| Scenario design | Levers act only on excess; overlaps combined probabilistically; low/base/high; no money | Avoids double counting and inflated benefits; no cost data means no ROI | Summing lever effects; inventing savings |
| Staged target | ≤ 6% then ≤ 5% | The base case reaches 5.3%. Committing to 5% would promise something the evidence doesn't support. | A round target with no basis |
| BI deliverable | Star schema, generated Power Query, DAX, spec, reconciliation checklist, Streamlit preview | Power BI Desktop needs Windows. I would not ship a `.pbip` I couldn't open and validate. | Hand-writing an unvalidated PBIP, or passing off a mockup as a dashboard |
| SQL Server | T-SQL generated with sqlglot plus hand-written overrides, parse-checked | No SQL Server available. Parse-checked is honest; "tested" would not be. | Claiming SQL Server compatibility |

## What each technique contributes
- **CTEs and window functions (LAG, running SUM, NTILE, RANK, ROW_NUMBER):** month-over-month growth, Pareto/ABC classes, seller deciles, first-order cohorts. All in one pass, without self-joins.
- **Validation SQL:** proves completeness (row counts), integrity (PK/FK), and cent-level financial reconciliation, *before* any insight is reported.
- **Mann-Whitney U:** review scores are ordinal, so a t-test on means would be inappropriate.
- **Chi-square and Wilson CIs:** binary outcomes (repeat purchase, late rates) with honest uncertainty.
- **Spearman correlation:** distance vs. delivery time is monotonic but skewed.
- **Logistic regression with average marginal effects:** controls for observed confounders and expresses the effect in percentage points.
- **Within-seller comparison (stratification):** controls for *unobserved* but stable seller traits.
- **Direct standardisation (distance-matched expectation):** compares lanes fairly.
- **Out-of-sample backtest:** tests whether a policy generalises.
- **Probabilistic overlap in scenarios:** prevents double-counting across interventions.
- **Power calculation:** sizes the pilot, so the recommendation can be tested.

## Likely interview questions
- **"How do you know lateness causes bad reviews?"** "I don't know it for certain. I know the link survives within-seller comparison and regression controls, and shows dose-response. That's strong observational evidence. Unobserved factors like transit damage could still travel with lateness, which is why the plan starts with a controlled lane pilot."
- **"Why not just promise longer delivery times?"** "I tested it out of sample. At the same average promise, route-calibrated promises cut the late rate by under half a point. Getting to about 5.5% needs about two more days of promise, with an unknown conversion cost."
- **"What's the ROI?"** "The data has no cost or margin, so I didn't compute one. I sized the outcome in late orders and reviews avoided, and listed the Finance inputs needed to convert that into money."
- **"What would you do with more time or data?"** "Get carrier IDs and tracking events to split post-handoff delay. Get conversion data to price the promise trade-off. Rerun on current data. Then run the pilot and replace my assumptions with measured effects."
- **"What surprised you?"** "That the obvious fix, recalibrating promises, didn't hold up out of sample. And that SP→RJ is badly served rather than just far away."
- **"What was hardest technically?"** "Making the SQL deterministic and portable: removing positional GROUP BY, adding tie-breakers, and handling MEDIAN, which has no T-SQL aggregate equivalent."

## Honest positioning
- This is a portfolio case study on public data. The stakeholders, targets and roadmap are hypothetical. Say so.
- If you used AI assistance to build any part of it, be ready to say so plainly and to explain every decision above in your own words. Interviewers will probe the reasoning, not the code volume.
- Study the topics in `docs/14_project_audit.md` §6 before claiming proficiency.
