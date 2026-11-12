"""Builds python/notebooks/analysis.ipynb (source of truth for the notebook's structure).

Run: python python/notebooks/build_notebook.py && make notebook
Markdown cells interpret; every number shown is computed by the code cell beneath it.
"""
from pathlib import Path

import nbformat as nbf

nb = nbf.v4.new_notebook()
md = lambda s: nbf.v4.new_markdown_cell(s.strip())  # noqa: E731
code = lambda s: nbf.v4.new_code_cell(s.strip())  # noqa: E731

nb.cells = [
    md("""
# Delivery Performance & Customer Satisfaction: analysis notebook

**Engagement question:** *How should the marketplace prioritise operational improvements to reduce delivery
delays and improve customer satisfaction?*

This notebook walks through the evidence chain behind the recommendations in `reports/executive_memo.md`.
It reads the outputs of the reproducible pipeline (`make pipeline`) and recomputes the key figures live.

| Section | Question |
|---|---|
| 1 | Is the data fit for purpose? |
| 2 | How big is the delivery problem, and is it worth solving? |
| 3 | Where do late deliveries originate? |
| 4 | Is the lateness-satisfaction link real, or a confounder? (correlation vs causation) |
| 5 | Can we fix it by changing the promise instead of the delivery? |
| 6 | What could the proposed interventions achieve? (scenario) |
| 7 | What we can and cannot conclude |

*Data: Olist Brazilian E-Commerce Public Dataset (Kaggle, CC BY-NC-SA 4.0). Analysis window: Jan 2017 - Aug 2018.*
"""),
    code("""
import json, sys
from pathlib import Path
import pandas as pd
from IPython.display import Image, display

ROOT = Path.cwd()
while not (ROOT / "requirements.txt").exists():
    ROOT = ROOT.parent
sys.path.insert(0, str(ROOT / "python"))
from olist_ba.clean import load_processed
from olist_ba import kpis

OUT = ROOT / "outputs"
q = lambda n: pd.read_csv(OUT / "sql" / "analysis" / f"{n}.csv")
chart = lambda f: display(Image(filename=str(ROOT / "assets" / "charts" / f), width=820))
km = json.loads((OUT / "key_metrics.json").read_text())
orders = load_processed("order_summary")
pd.set_option("display.width", 160); pd.set_option("display.max_columns", 20)
print(f"{len(orders):,} orders loaded | interpreter: {Path(sys.executable).parent.parent.name}/{Path(sys.executable).name}")
"""),
    md("""
## 1. Data fitness

Before analysing anything, the pipeline proves the data is complete and internally consistent:
row counts match from raw to modelled layer, keys are unique, every foreign key resolves, typed totals
reconcile to the cent, and an **independent pandas implementation** of all cleaning rules reproduces the SQL
view column-for-column (tested in `tests/test_reconciliation.py`).
"""),
    code("""
checks = pd.concat([pd.read_csv(p).assign(suite=p.stem) for p in sorted((OUT / "sql" / "validation").glob("*.csv"))])
print(checks["status"].value_counts().to_string())
checks[checks["status"] == "INFO"][["suite", "check_name", "actual"]]
"""),
    md("""
The `INFO` rows are known data-quality characteristics that are **kept and flagged**, not deleted
(see `docs/04_data_cleaning_log.md`). For example, 1,359 orders record a carrier handoff before payment approval;
they are excluded only from the stage-duration medians where that ordering matters.
"""),
    md("## 2. Size of the problem"),
    code("""
k = kpis.kpi_scorecard(orders)
pd.Series(k).to_frame("value")
"""),
    code("chart('04_delivery_vs_review.png')"),
    md("""
About 7% of delivered orders arrive after the date promised at checkout. That sounds small, but the review
distribution changes sharply once an order is late: on-time orders average above 4 stars, orders 8+ days late
average 1.7. Because 97% of customers buy only once in the window, reviews are the platform's main public
reputation signal for new buyers. That makes them, rather than repeat purchases, the main reason lateness matters.
"""),
    md("## 3. Where late deliveries originate"),
    code("""
dec = pd.read_csv(OUT / "root_cause" / "late_decomposition.csv")
dec
"""),
    code("chart('13_late_order_origin.png'); chart('05_fulfilment_stage_trend.png')"),
    code("""
lanes = pd.read_csv(OUT / "root_cause" / "top_routes_excess_late.csv")
print(f"Top 15 lanes: {km['top15_lanes_share_of_excess_late']:.0%} of excess late orders "
      f"on {km['top15_lanes_share_of_volume']:.0%} of delivered volume")
lanes.head(10)
"""),
    code("chart('14_lane_excess_late.png')"),
    md("""
**Reading:** most late orders are not caused by sellers shipping late. The seller hands over on time and the
delay accrues afterwards, in transit. The problem is also concentrated in time (three peak months) and in
space (a few lanes out of São Paulo, led by SP → RJ). Seller SLA misses are a smaller but separate driver:
an order whose seller misses the shipping limit is ~4x as likely to arrive late.

*Limitation:* the dataset does not identify the carrier, so "post-handoff delay" cannot be split between
carrier performance, regional infrastructure and the 2018 events that may explain the Feb-Mar spike. That split
is a data request in the requirements document, not something this analysis can claim.
"""),
    md("""
## 4. Correlation vs causation: is the satisfaction gap real?

A raw comparison could be confounded: a poor seller might ship slowly *and* sell poor products, which would
produce bad reviews regardless of lateness. Three increasingly strict comparisons:
"""),
    code("""
rc = json.loads((OUT / "root_cause" / "root_cause_summary.json").read_text())["controlled_review_effect"]
pd.DataFrame({
    "method": ["Raw difference", "Within the same seller", "Logistic regression with controls (avg marginal effect)"],
    "gap in 1-2 star rate (pp)": [rc["raw_gap_pp"], rc["within_seller_gap_pp"], rc["logit_avg_marginal_effect_pp"]],
    "controls for": ["nothing", "everything stable about the seller", "price, freight, basket, interstate, state, category, month"],
})
"""),
    code("pd.Series(rc['dose_response_low_review_by_days_late'], name='1-2 star rate by days late')"),
    md("""
The gap barely moves under controls (about 54 → 53 → 51 pp) and rises with the number of days late (a dose-response
pattern). The review is written after delivery, so reverse causation is implausible. This is **strong
observational evidence**, but it is still not proof: unobserved order-level factors such as transit damage
could travel with lateness. The memo therefore recommends a **controlled pilot** on target lanes before scaling.
"""),
    md("## 5. Can we just change the promise?"),
    code("pd.read_csv(OUT / 'root_cause' / 'estimate_backtest.csv').iloc[[0, 1, 11, 14, 16, 18]]"),
    code("chart('16_promise_backtest.png')"),
    md("""
An out-of-sample backtest (calibrate on 2017, test on 2018) shows route-level promises sit on the **same
trade-off curve** as the current estimate. At an equal average promise the late rate improves by under half a
point. Re-setting promises is therefore a low-value lever. The physical delivery has to improve.
"""),
    md("## 6. Scenario: what could the interventions achieve?"),
    code("""
sc = pd.read_csv(OUT / "scenarios" / "scenario_results.csv")
sc.pivot(index="lever", columns="case", values="new_late_rate")
"""),
    code("chart('15_scenario_impact.png')"),
    md("""
Assumptions are listed in `docs/08_scenario_analysis.md` and are adjustable in the dashboard's scenario page.
Each lever acts only on the *excess* late rate of its segment, and overlaps are removed. Under base
assumptions, the late rate falls from about 7.9% to about 5.3% for the baseline year. That **misses a 5% target**,
which is why the charter sets a staged target and why the pilot's measured effect should replace these
assumptions.
"""),
    md("""
## 7. What we can and cannot conclude

| Conclusion | Evidence grade |
|---|---|
| Late deliveries are concentrated in post-handoff transit, peak months and a few lanes | **Observed** (descriptive, complete data) |
| Late delivery is associated with a ~51-54 pp higher 1-2 star rate, robust to controls | **Strong association** (not proven causal) |
| Seller SLA misses are associated with a ~4x higher late rate | **Association** (seller confounding possible) |
| Lane interventions would reduce late deliveries | **Hypothesis**: test with a pilot |
| Revenue / retention impact of fixing lateness | **Not quantified.** The repeat-purchase effect is statistically significant but small in absolute terms, and the data contains no cost or margin. |
"""),
    code("""
print(f"Repeat rate after a late first order: {km['repeat_rate_first_late']:.2%} vs on time {km['repeat_rate_first_on_time']:.2%} "
      f"(p = {km['repeat_p_value']:.4f})")
"""),
]
nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
out = Path(__file__).with_name("analysis.ipynb")
nbf.write(nb, out)
print(f"wrote {out}")
