"""Business charts -> assets/charts/*.png.

Every chart is built from the validated SQL outputs (outputs/sql/analysis/*.csv) or the
statistics file (outputs/stats/stats_summary.json), so images always match the numbers in
the docs. Each title states the business question's answer, not just the metric name.

Palette: reference data-viz palette (blue / orange categorical slots, gray for context).
Usage: python -m olist_ba.charts
"""
from __future__ import annotations

import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.ticker as mtick  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from .config import ASSETS, OUTPUTS  # noqa: E402

BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
GRAY, GRID = "#b4b2aa", "#e6e5e0"
INK, INK2, SURFACE = "#0b0b0b", "#52514e", "#fcfcfb"
SOURCE = "Source: Olist Brazilian E-Commerce Public Dataset (Kaggle, CC BY-NC-SA 4.0). Window: Jan 2017 - Aug 2018."

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "font.family": "DejaVu Sans", "font.size": 10.5, "text.color": INK,
    "axes.edgecolor": GRID, "axes.labelcolor": INK2, "axes.titlesize": 13, "axes.titleweight": "bold",
    "axes.titlelocation": "left", "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8, "axes.axisbelow": True,
    "xtick.color": INK2, "ytick.color": INK2, "xtick.major.size": 0, "ytick.major.size": 0,
    "legend.frameon": False, "lines.linewidth": 2,
})


def _q(name: str) -> pd.DataFrame:
    return pd.read_csv(OUTPUTS / "sql" / "analysis" / f"{name}.csv")


def _stats() -> dict:
    return json.loads((OUTPUTS / "stats" / "stats_summary.json").read_text())


def _finish(fig, ax, fname: str, subtitle: str) -> None:
    ax.text(0, 1.02, subtitle, transform=ax.transAxes, color=INK2, fontsize=10, va="bottom")
    fig.text(0.01, 0.01, SOURCE, color=INK2, fontsize=7.5)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    ASSETS.mkdir(parents=True, exist_ok=True)
    fig.savefig(ASSETS / fname, dpi=150)
    plt.close(fig)


def brl(x, _=None) -> str:
    if abs(x) >= 1e6:
        return f"R${x / 1e6:.1f}M"
    if abs(x) >= 1e3:
        return f"R${x / 1e3:.0f}K"
    return f"R${x:.0f}"


# ----------------------------------------------------------------------------- charts
def revenue_trend() -> None:
    d = _q("q02_monthly_revenue_trend")
    d["purchase_month"] = pd.to_datetime(d["purchase_month"])
    fig, ax = plt.subplots(figsize=(10, 5.2))
    ax.bar(d["purchase_month"], d["product_revenue"], width=20, color=BLUE, alpha=0.35, label="Monthly product revenue")
    ax.plot(d["purchase_month"], d["revenue_3m_moving_avg"], color=BLUE, label="3-month moving average")
    ax.yaxis.set_major_formatter(mtick.FuncFormatter(brl))
    peak = d.loc[d["product_revenue"].idxmax()]
    ax.annotate(f"Nov 2017 (Black Friday)\n{brl(peak['product_revenue'])}", (peak["purchase_month"], peak["product_revenue"]),
                xytext=(-175, -40), textcoords="offset points", color=INK2, fontsize=9,
                arrowprops=dict(arrowstyle="-", color=INK2, lw=0.8))
    ax.legend(loc="upper left")
    ax.set_title("Revenue grew fast through 2017, then plateaued in 2018", pad=24)
    _finish(fig, ax, "01_monthly_revenue_trend.png",
            "Monthly product revenue (item price, excl. freight), revenue orders only")


def yoy_growth() -> None:
    d = _q("q03_yoy_same_period")
    m = d[d["month_num"] != 99]
    tot = d[d["month_num"] == 99].iloc[0]
    labels = pd.to_datetime(m["month_num"].astype(int).astype(str), format="%m").dt.strftime("%b")
    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.bar(labels, m["revenue_yoy_pct"], color=BLUE, width=0.6)
    ax.bar_label(bars, labels=[f"+{v:.0f}%" for v in m["revenue_yoy_pct"]], padding=3, color=INK, fontsize=9.5)
    ax.yaxis.set_major_formatter(mtick.PercentFormatter(decimals=0))
    ax.set_title("Year-over-year growth slowed every month in 2018", pad=24)
    _finish(fig, ax, "02_yoy_growth_deceleration.png",
            f"Revenue growth, 2018 vs same month 2017. Jan-Aug total: +{tot['revenue_yoy_pct']:.0f}%")


def category_pareto() -> None:
    d = _q("q04_category_pareto").head(15).iloc[::-1]
    fig, ax = plt.subplots(figsize=(10, 6.2))
    bars = ax.barh(d["category"].str.replace("_", " "), d["revenue"], color=BLUE, height=0.65)
    ax.bar_label(bars, labels=[f"{brl(r)}  (cum. {c:.0%})" for r, c in zip(d["revenue"], d["cumulative_share"])],
                 padding=4, color=INK2, fontsize=8.5)
    ax.xaxis.set_major_formatter(mtick.FuncFormatter(brl))
    ax.set_xlim(0, d["revenue"].max() * 1.35)
    ax.grid(axis="y", visible=False)
    n_a = (_q("q04_category_pareto")["abc_class"] == "A").sum()
    ax.set_title(f"{n_a} of 74 categories generate ~80% of revenue", pad=24)
    _finish(fig, ax, "03_category_pareto.png", "Top 15 categories by product revenue; label shows cumulative share of total")


def delivery_vs_review() -> None:
    d = _q("q07_delivery_vs_review")
    lab = d["delivery_vs_estimate"].str[3:]
    colors = [ORANGE if "late" in s else BLUE for s in lab]
    fig, ax = plt.subplots(figsize=(10, 5.2))
    bars = ax.bar(lab, d["avg_review"], color=colors, width=0.62)
    ax.bar_label(bars, labels=[f"{v:.2f}\n({r:.0%} 1-2★)" for v, r in zip(d["avg_review"], d["low_review_rate"])],
                 padding=3, fontsize=8.5, color=INK)
    ax.set_ylim(0, 5.4)
    ax.set_ylabel("Average review score (1-5)")
    ax.tick_params(axis="x", labelsize=9)
    ax.grid(axis="x", visible=False)
    ax.legend(handles=[plt.Rectangle((0, 0), 1, 1, color=BLUE), plt.Rectangle((0, 0), 1, 1, color=ORANGE)],
              labels=["On/before estimated date", "After estimated date"], loc="upper right")
    ax.set_title("Late deliveries are associated with sharply worse reviews", pad=24)
    _finish(fig, ax, "04_delivery_vs_review.png",
            "Delivered orders by actual vs promised delivery date; label = avg score and share of 1-2 star reviews")


def fulfilment_stages() -> None:
    d = _q("q08_fulfilment_stage_trend")
    d["purchase_month"] = pd.to_datetime(d["purchase_month"])
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(10, 7), sharex=True, gridspec_kw={"height_ratios": [1, 1.2]})
    a1.plot(d["purchase_month"], d["late_rate"], color=ORANGE, marker="o", markersize=4)
    a1.yaxis.set_major_locator(mtick.MultipleLocator(0.05))
    a1.yaxis.set_major_formatter(mtick.PercentFormatter(1, decimals=0))
    a1.set_ylim(0, None)
    a1.set_ylabel("Late delivery rate")
    a1.set_title("Late-delivery spikes track carrier transit time, not seller handoff", pad=24)
    a1.text(0, 1.02, "Monthly late rate (top) and median days per fulfilment stage (bottom), delivered orders",
            transform=a1.transAxes, color=INK2, fontsize=10, va="bottom")
    a2.plot(d["purchase_month"], d["median_carrier_to_customer_days"], color=BLUE, label="Carrier -> customer")
    a2.plot(d["purchase_month"], d["median_seller_to_carrier_days"], color=AQUA, label="Approval -> carrier (seller)")
    a2.set_ylabel("Median days")
    for line, lab in [(a2.lines[0], "Carrier -> customer"), (a2.lines[1], "Approval -> carrier (seller)")]:
        a2.text(d["purchase_month"].iloc[-1], line.get_ydata()[-1], "  " + lab, color=INK2, fontsize=9, va="center")
    a2.legend(loc="upper left")
    a2.set_xlim(d["purchase_month"].min(), d["purchase_month"].max() + pd.Timedelta(days=150))
    fig.text(0.01, 0.01, SOURCE, color=INK2, fontsize=7.5)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(ASSETS / "05_fulfilment_stage_trend.png", dpi=150)
    plt.close(fig)


def state_experience() -> None:
    d = _q("q06_state_performance")
    fig, ax = plt.subplots(figsize=(10, 6))
    size = d["product_revenue"] / d["product_revenue"].max() * 1800 + 25
    hi = d["customer_state"].isin(["RJ"])
    ax.scatter(d.loc[~hi, "on_time_rate"], d.loc[~hi, "avg_review"], s=size[~hi], color=BLUE, alpha=0.55,
               edgecolor=SURFACE, linewidth=1.5)
    ax.scatter(d.loc[hi, "on_time_rate"], d.loc[hi, "avg_review"], s=size[hi], color=ORANGE, alpha=0.85,
               edgecolor=SURFACE, linewidth=1.5)
    for _, r in d.iterrows():
        if r["revenue_rank"] <= 8 or r["on_time_rate"] < 0.84:
            off = (8, -14) if r["customer_state"] == "PR" else (6, 4)
            ax.annotate(r["customer_state"], (r["on_time_rate"], r["avg_review"]), xytext=off,
                        textcoords="offset points", fontsize=9, color=INK)
    ax.xaxis.set_major_locator(mtick.MultipleLocator(0.04))
    ax.xaxis.set_major_formatter(mtick.PercentFormatter(1, decimals=0))
    ax.set_xlabel("On-time delivery rate")
    ax.set_ylabel("Average review score")
    ax.set_title("Rio de Janeiro: 13% of revenue with below-par delivery and reviews", pad=24)
    _finish(fig, ax, "06_state_delivery_vs_review.png",
            "Customer states; bubble area = product revenue. RJ highlighted in orange")


def distance_bands() -> None:
    b = pd.DataFrame(_stats()["distance_vs_delivery"]["by_distance_band"])
    rho = _stats()["distance_vs_delivery"]["spearman_distance_delivery_days"]
    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.bar(b["distance_band"], b["median_delivery_days"], color=BLUE, width=0.6)
    ax.bar_label(bars, labels=[f"{d:.1f} days\n{lr:.1%} late" for d, lr in zip(b["median_delivery_days"], b["late_rate"])],
                 padding=3, fontsize=9, color=INK)
    ax.set_ylim(0, b["median_delivery_days"].max() * 1.3)
    ax.set_ylabel("Median delivery days")
    ax.grid(axis="x", visible=False)
    ax.set_title("Delivery time and late rate rise with seller-to-customer distance", pad=24)
    _finish(fig, ax, "07_distance_vs_delivery.png",
            f"Single-seller delivered orders by straight-line distance (zip centroids). Spearman rho = {rho:.2f}")


def seller_concentration() -> None:
    d = _q("q10_seller_concentration")
    fig, ax = plt.subplots(figsize=(10, 5))
    colors = [BLUE if i == 1 else GRAY for i in d["revenue_decile"]]
    bars = ax.bar(d["revenue_decile"].astype(str), d["revenue_share_pct"], color=colors, width=0.62)
    ax.bar_label(bars, labels=[f"{v:.1f}%" for v in d["revenue_share_pct"]], padding=3, fontsize=9)
    ax.yaxis.set_major_formatter(mtick.PercentFormatter(decimals=0))
    ax.set_xlabel("Seller revenue decile (1 = top 10% of sellers)")
    ax.grid(axis="x", visible=False)
    ax.set_title(f"The top 10% of sellers ({int(d.loc[0, 'sellers'])}) generate {d.loc[0, 'revenue_share_pct']:.0f}% of revenue", pad=24)
    _finish(fig, ax, "08_seller_concentration.png", "Share of product revenue by seller decile")


def customer_frequency() -> None:
    d = _q("q12_customer_frequency")
    x = range(len(d))
    fig, ax = plt.subplots(figsize=(10, 5))
    w = 0.36
    b1 = ax.bar([i - w / 2 - 0.01 for i in x], d["customer_share_pct"], width=w, color=BLUE, label="Share of customers")
    b2 = ax.bar([i + w / 2 + 0.01 for i in x], d["revenue_share_pct"], width=w, color=ORANGE, label="Share of revenue")
    for b in (b1, b2):
        ax.bar_label(b, labels=[f"{v:.1f}%" for v in b.datavalues], padding=3, fontsize=9)
    ax.set_xticks(list(x), d["frequency_band"])
    ax.yaxis.set_major_formatter(mtick.PercentFormatter(decimals=0))
    ax.set_ylim(0, 110)
    ax.grid(axis="x", visible=False)
    ax.legend(loc="upper right")
    ax.set_title("97% of customers bought only once in 20 months", pad=24)
    _finish(fig, ax, "09_customer_frequency.png", "Customers (customer_unique_id) by number of revenue orders in the window")


def seller_sla() -> None:
    d = _q("q09_seller_shipping_sla").sort_values("seller_handoff", ascending=False)
    metrics = [("late_delivery_rate", "Late delivery rate"), ("low_review_rate", "1-2 star review rate")]
    fig, ax = plt.subplots(figsize=(10, 5))
    w = 0.36
    for j, (col, lab) in enumerate(metrics):
        xs = [i + (j - 0.5) * (w + 0.02) for i in range(len(d))]
        b = ax.bar(xs, d[col], width=w, color=[BLUE, ORANGE][j], label=lab)
        ax.bar_label(b, labels=[f"{v:.1%}" for v in d[col]], padding=3, fontsize=9)
    ax.set_xticks(range(len(d)), [f"{h}\n({s:.1f}% of orders)" for h, s in zip(d["seller_handoff"], d["share_pct"])])
    ax.yaxis.set_major_formatter(mtick.PercentFormatter(1, decimals=0))
    ax.grid(axis="x", visible=False)
    ax.legend(loc="upper left")
    ax.set_title("Orders where the seller missed the shipping deadline are ~4x more likely to arrive late", pad=24)
    _finish(fig, ax, "10_seller_sla_impact.png", "Delivered orders, by whether the seller handed over to the carrier by the shipping-limit date")


def freight_burden() -> None:
    d = _q("q18_freight_burden_by_price_band")
    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.bar(d["price_band"].str[3:], d["freight_to_price_ratio"], color=BLUE, width=0.6)
    ax.bar_label(bars, labels=[f"{v:.0%}\n({n:,} orders)" for v, n in zip(d["freight_to_price_ratio"], d["orders"])],
                 padding=3, fontsize=9)
    ax.yaxis.set_major_formatter(mtick.PercentFormatter(1, decimals=0))
    ax.set_ylim(0, d["freight_to_price_ratio"].max() * 1.3)
    ax.set_xlabel("Order product value")
    ax.grid(axis="x", visible=False)
    ax.set_title("On orders under R$50, freight adds almost half the item price", pad=24)
    _finish(fig, ax, "11_freight_burden.png", "Freight charged as a share of product value, by order value band")


def installments() -> None:
    d = _q("q17_installments_vs_aov")
    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.bar(d["installment_band"], d["aov"], color=BLUE, width=0.6)
    ax.bar_label(bars, labels=[f"{brl(a)} AOV\n{s:.0f}% of revenue" for a, s in zip(d["aov"], d["revenue_share_pct"])],
                 padding=3, fontsize=9)
    ax.yaxis.set_major_formatter(mtick.FuncFormatter(brl))
    ax.set_ylim(0, d["aov"].max() * 1.3)
    ax.set_xlabel("Number of payment instalments")
    ax.grid(axis="x", visible=False)
    ax.set_title("Instalment orders carry much higher order values", pad=24)
    _finish(fig, ax, "12_installments_vs_aov.png", "Average order value (product revenue) by maximum instalments chosen")


ALL = [revenue_trend, yoy_growth, category_pareto, delivery_vs_review, fulfilment_stages, state_experience,
       distance_bands, seller_concentration, customer_frequency, seller_sla, freight_burden, installments]


# ----------------------------------------------------------------------------- decision charts
def _rc(name: str) -> pd.DataFrame:
    return pd.read_csv(OUTPUTS / "root_cause" / f"{name}.csv")


def late_origin() -> None:
    d = _rc("late_decomposition").set_index("origin").drop("Total")
    cols = ["Other 17 months", "Peak months (Nov-17, Feb-18, Mar-18)"]
    labels = ["Seller missed\nshipping limit", "Seller on time, delayed\nafter carrier handoff"]
    fig, ax = plt.subplots(figsize=(10, 4.6))
    left = [0, 0]
    total = d["Total"].sum()
    for col, color, lab in zip(cols, [BLUE, ORANGE], ["Other 17 months", "3 peak months (Nov-17, Feb-18, Mar-18)"]):
        vals = d[col].tolist()
        bars = ax.barh(labels, vals, left=left, color=color, height=0.55, label=lab, edgecolor=SURFACE, linewidth=2)
        ax.bar_label(bars, labels=[f"{v:,} ({v / total:.0%})" for v in vals], label_type="center", color="white", fontsize=9.5)
        left = [a + b for a, b in zip(left, vals)]
    for i, t in enumerate(d["Total"]):
        ax.text(t + 60, i, f"{t / total:.0%} of late orders", va="center", color=INK, fontsize=10, fontweight="bold")
    ax.set_xlim(0, max(left) * 1.3)
    ax.invert_yaxis()
    ax.grid(axis="y", visible=False)
    ax.set_xlabel("Late delivered orders (single-seller, Jan 2017 - Aug 2018)")
    ax.legend(loc="upper right")
    ax.set_title("Most late orders go wrong after the carrier picks them up", pad=24)
    _finish(fig, ax, "13_late_order_origin.png",
            f"{total:,} late orders by where the delay began, split by peak vs other months")


def lane_excess() -> None:
    d = _rc("top_routes_excess_late").head(12).iloc[::-1]
    fig, ax = plt.subplots(figsize=(10, 5.8))
    colors = [ORANGE if r == "SP->RJ" else BLUE for r in d["route"]]
    bars = ax.barh(d["route"].str.replace("->", " → "), d["excess_late"], color=colors, height=0.62)
    ax.bar_label(bars, labels=[f"{e:,.0f}  ({lr:.1%} late on {n:,} orders)" for e, lr, n in
                               zip(d["excess_late"], d["late_rate"], d["delivered"])], padding=4, fontsize=8.8, color=INK2)
    ax.set_xlim(0, d["excess_late"].max() * 1.55)
    ax.grid(axis="y", visible=False)
    ax.set_xlabel("Excess late orders vs platform average late rate (6.9%)")
    ax.set_title("A handful of lanes drive the excess late deliveries; SP → RJ alone is the largest", pad=24)
    _finish(fig, ax, "14_lane_excess_late.png",
            "Seller state → customer state lanes with >= 30 delivered orders, ranked by late orders above expectation")


def scenario_impact() -> None:
    t = pd.read_csv(OUTPUTS / "scenarios" / "scenario_results.csv")
    names = {"L1": "L1 Lane recovery (15 lanes)", "L2": "L2 Seller SLA enforcement", "L4": "L4 Peak-season capacity",
             "Combined (L1+L2+L4, overlap removed)": "Combined (overlap removed)"}
    p = t.pivot(index="lever", columns="case", values="late_rate_change_pp").loc[list(names)]
    fig, ax = plt.subplots(figsize=(10, 5))
    y = range(len(p))
    colors = [BLUE, BLUE, BLUE, ORANGE]
    ax.barh(list(y), -p["base"], color=colors, height=0.55)
    ax.errorbar(-p["base"], list(y), xerr=[(-p["base"]) - (-p["low"]), (-p["high"]) - (-p["base"])],
                fmt="none", ecolor=INK, elinewidth=1.2, capsize=4)
    for i, (lo, b, hi) in enumerate(zip(-p["low"], -p["base"], -p["high"])):
        ax.text(hi + 0.08, i, f"-{b:.2f} pp  (range -{lo:.2f} to -{hi:.2f})", va="center", fontsize=9, color=INK2)
    ax.set_yticks(list(y), [names[k] for k in p.index])
    ax.invert_yaxis()
    ax.set_xlim(0, (-p["high"]).max() * 1.6)
    ax.grid(axis="y", visible=False)
    base = t["baseline_late_rate"].iloc[0]
    ax.set_xlabel(f"Reduction in late-delivery rate, percentage points (baseline {base:.1%})")
    ax.set_title("Scenario: combined levers could cut the late rate by ~2.5 pp (base case)", pad=24)
    _finish(fig, ax, "15_scenario_impact.png",
            "Scenario model, Sep 2017 - Aug 2018 orders. Bars = base case, whiskers = low/high. Not a forecast.")


def promise_backtest() -> None:
    b = _rc("estimate_backtest")
    cur = b.iloc[0]
    r = b.iloc[1:]
    m = b[b["is_matched_to_current_avg_promise"]].iloc[0]
    fig, ax = plt.subplots(figsize=(10, 5.2))
    ax.plot(r["avg_promised_days"], r["late_rate"], color=BLUE, marker="o", markersize=4.5, zorder=2,
            label="Route-calibrated promise (P80 ... P97 of 2017 delivery times)")
    ax.scatter(cur["avg_promised_days"], cur["late_rate"], s=140, color=ORANGE, zorder=3, edgecolor=SURFACE,
               linewidth=2, label="Current platform estimate")
    for q in (0.80, 0.90, 0.95):
        row = r[np.isclose(r["quantile"], q)].iloc[0]
        ax.annotate(f"P{int(q * 100)}", (row["avg_promised_days"], row["late_rate"]), xytext=(-6, -16),
                    textcoords="offset points", fontsize=9, color=INK2)
    ax.annotate(f"Same avg promise ({m['avg_promised_days']:.1f} d):\nroute {m['late_rate']:.1%} vs current {cur['late_rate']:.1%} late",
                (m["avg_promised_days"], m["late_rate"]), xytext=(25, 40), textcoords="offset points", fontsize=9.5,
                arrowprops=dict(arrowstyle="-", color=INK2, lw=0.8))
    ax.yaxis.set_major_locator(mtick.MultipleLocator(0.05))
    ax.yaxis.set_major_formatter(mtick.PercentFormatter(1, decimals=0))
    ax.set_xlabel("Average promised delivery days")
    ax.set_ylabel("Late-delivery rate (test period)")
    ax.set_ylim(0, b["late_rate"].max() * 1.15)
    ax.legend(loc="upper right")
    ax.set_title("Recalibrating promises by route is a trade-off, not a free win", pad=24)
    _finish(fig, ax, "16_promise_backtest.png",
            f"Out-of-sample backtest: calibrated on 2017 deliveries, tested on {int(b['test_orders'].iloc[0]):,} Jan-Aug 2018 orders")


ALL += [late_origin, lane_excess, scenario_impact, promise_backtest]


def lane_vs_distance() -> None:
    d = _rc("lane_distance_matched").sort_values("ratio_actual_to_expected")
    fig, ax = plt.subplots(figsize=(10, 5.8))
    y = list(range(len(d)))
    anomalous = d["ratio_actual_to_expected"] >= 1.5
    ax.hlines(y, d["distance_matched_expected"], d["actual_late_rate"], color=GRAY, linewidth=2, zorder=1)
    ax.scatter(d["distance_matched_expected"], y, s=70, color=SURFACE, edgecolor=INK2, linewidth=1.5, zorder=2,
               label="Expected for its distance (other lanes, same 50 km bins)")
    ax.scatter(d["actual_late_rate"], y, s=80, zorder=3, edgecolor=SURFACE, linewidth=1.5,
               color=[ORANGE if a else BLUE for a in anomalous], label="Actual late rate")
    for i, (_, r) in enumerate(d.iterrows()):
        ax.text(max(r["actual_late_rate"], r["distance_matched_expected"]) + 0.006, i,
                f"{r['ratio_actual_to_expected']:.2f}x  ({int(r['orders']):,} orders, ~{int(r['median_km']):,} km)",
                va="center", fontsize=8.8, color=INK2)
    ax.set_yticks(y, d["route"].str.replace("->", " → "))
    ax.xaxis.set_major_locator(mtick.MultipleLocator(0.05))
    ax.xaxis.set_major_formatter(mtick.PercentFormatter(1, decimals=0))
    ax.set_xlim(0, d["actual_late_rate"].max() * 1.6)
    ax.grid(axis="y", visible=False)
    ax.set_xlabel("Late-delivery rate")
    ax.legend(loc="lower right", fontsize=9)
    ax.set_title("Distance does not explain SP → RJ: it runs 2.7x the late rate expected for its distance", pad=24)
    _finish(fig, ax, "17_lane_vs_distance.png",
            "Top excess-late lanes plus SP→MG / SP→SP for reference. Orange = actual ≥ 1.5x distance-matched expectation")


ALL += [lane_vs_distance]


def main() -> None:
    for f in ALL:
        f()
    print(f"Wrote {len(ALL)} charts to {ASSETS}")


if __name__ == "__main__":
    main()
