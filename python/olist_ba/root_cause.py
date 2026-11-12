"""Root-cause analysis for late deliveries and their link to customer satisfaction.

Decision supported: which operational improvements should the marketplace prioritise to
reduce delivery delays and improve customer satisfaction?

Analyses (outputs in outputs/root_cause/):
  1. decompose_late_orders   - where in the fulfilment chain late orders originate
  2. seller_concentration    - do a few sellers drive a disproportionate share of late orders?
  3. route_concentration     - which seller-state -> customer-state lanes drive excess late orders?
  4. controlled_review_effect- does the late -> low-review association survive controls?
                               (raw gap, within-seller stratified gap, logistic regression)
  5. estimate_backtest       - would route-calibrated delivery promises reduce late deliveries
                               out of sample (calibrate on 2017, test on Jan-Aug 2018)?

Evidence language used throughout: "associated with" for observational results.
Nothing here proves causation; see docs/06_insights_and_evidence.md for the evidence grading.

Usage: python -m olist_ba.root_cause
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

from .clean import load_processed
from .config import OUTPUTS
from .kpis import fulfilment_scope

OUT = OUTPUTS / "root_cause"
PEAK_MONTHS = [pd.Timestamp("2017-11-01"), pd.Timestamp("2018-02-01"), pd.Timestamp("2018-03-01")]
MIN_SELLER_ORDERS = 30
MIN_ROUTE_ORDERS = 30


# ----------------------------------------------------------------------------- base table
def delivered_with_seller() -> pd.DataFrame:
    """Delivered in-window orders with a single seller, enriched with seller, route and product attributes."""
    o = fulfilment_scope(load_processed("order_summary"))
    items, sellers = load_processed("order_items"), load_processed("sellers")
    products, cats = load_processed("products"), load_processed("categories")
    first = (items.sort_values(["order_id", "price"], ascending=[True, False])
                  .drop_duplicates("order_id")[["order_id", "seller_id", "product_id", "shipping_limit_ts"]])
    d = (o[o["seller_count"] == 1]
         .merge(first, on="order_id")
         .merge(sellers[["seller_id", "state"]].rename(columns={"state": "seller_state"}), on="seller_id")
         .merge(products[["product_id", "category_pt", "weight_g"]], on="product_id", how="left")
         .merge(cats[["category_pt", "category_en"]], on="category_pt", how="left"))
    d["route"] = d["seller_state"] + "->" + d["customer_state"]
    d["is_peak_month"] = d["purchase_month"].isin(PEAK_MONTHS).astype(int)
    d["low_review"] = np.where(d["review_score"].isna(), np.nan, (d["review_score"] <= 2).astype(float))
    d["delivery_days_int"] = (d["delivered_customer_ts"].dt.normalize() - d["purchase_date"]).dt.days
    return d


# ----------------------------------------------------------------------------- 1
def decompose_late_orders(d: pd.DataFrame) -> pd.DataFrame:
    late = d[d["is_late"] == 1].copy()
    late["origin"] = np.where(late["seller_shipped_late"] == 1, "Seller missed shipping limit",
                              "Seller on time -> delay after carrier handoff")
    late["period"] = np.where(late["is_peak_month"] == 1, "Peak months (Nov-17, Feb-18, Mar-18)", "Other 17 months")
    t = late.pivot_table(index="origin", columns="period", values="order_id", aggfunc="count", fill_value=0)
    t["Total"] = t.sum(axis=1)
    t.loc["Total"] = t.sum()
    share = (t / t.loc["Total", "Total"]).round(4)
    share.columns = [f"{c} (share)" for c in share.columns]
    return pd.concat([t, share], axis=1).reset_index()


# ----------------------------------------------------------------------------- 2
def seller_concentration(d: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    base = d["is_late"].mean()
    s = d.groupby("seller_id").agg(seller_state=("seller_state", "first"), delivered=("order_id", "size"),
                                   late=("is_late", "sum"), sla_miss=("seller_shipped_late", "sum"),
                                   low_review_rate=("low_review", "mean"))
    s["late_rate"] = s["late"] / s["delivered"]
    s["expected_late"] = s["delivered"] * base
    s["excess_late"] = s["late"] - s["expected_late"]
    s = s.sort_values("excess_late", ascending=False)
    eligible = s[s["delivered"] >= MIN_SELLER_ORDERS]
    total_excess_pos = s.loc[s["excess_late"] > 0, "excess_late"].sum()
    top = eligible.head(50)
    by_late = s.sort_values("late", ascending=False)
    k10 = int(np.ceil(len(s) * 0.10))
    summary = {
        "sellers_with_deliveries": int(len(s)),
        "platform_late_rate": round(float(base), 4),
        "share_of_late_orders_from_top10pct_sellers_by_late_count": round(float(by_late.head(k10)["late"].sum() / s["late"].sum()), 4),
        "share_of_delivered_orders_from_same_sellers": round(float(by_late.head(k10)["delivered"].sum() / s["delivered"].sum()), 4),
        "share_of_sla_misses_from_top10pct_sellers_by_misses": round(float(
            s.sort_values("sla_miss", ascending=False).head(k10)["sla_miss"].sum() / s["sla_miss"].sum()), 4),
        "eligible_sellers_min_orders": MIN_SELLER_ORDERS,
        "top50_eligible_sellers_excess_late_orders": round(float(top["excess_late"].sum()), 1),
        "top50_share_of_all_positive_excess": round(float(top["excess_late"].sum() / total_excess_pos), 4),
        "top50_late_rate": round(float(top["late"].sum() / top["delivered"].sum()), 4),
        "top50_share_of_delivered_orders": round(float(top["delivered"].sum() / s["delivered"].sum()), 4),
    }
    return top.round(4).reset_index(), summary


# ----------------------------------------------------------------------------- 3
def route_concentration(d: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    base = d["is_late"].mean()
    r = d.groupby("route").agg(delivered=("order_id", "size"), late=("is_late", "sum"),
                               median_days=("delivery_days", "median"),
                               avg_promised_days=("promised_days", "mean"),
                               low_review_rate=("low_review", "mean"))
    r["late_rate"] = r["late"] / r["delivered"]
    r["excess_late"] = r["late"] - r["delivered"] * base
    r = r[r["delivered"] >= MIN_ROUTE_ORDERS].sort_values("excess_late", ascending=False)
    top = r.head(15)
    pos = r.loc[r["excess_late"] > 0, "excess_late"].sum()
    to_rj = d[d["customer_state"] == "RJ"]
    summary = {
        "routes_with_min_orders": int(len(r)),
        "top15_routes_excess_late": round(float(top["excess_late"].sum()), 1),
        "top15_share_of_positive_excess": round(float(top["excess_late"].sum() / pos), 4),
        "top15_share_of_delivered": round(float(top["delivered"].sum() / len(d)), 4),
        "sp_to_rj_late_rate": round(float(d.loc[d["route"] == "SP->RJ", "is_late"].mean()), 4),
        "sp_to_rj_delivered": int((d["route"] == "SP->RJ").sum()),
        "sp_to_sp_late_rate": round(float(d.loc[d["route"] == "SP->SP", "is_late"].mean()), 4),
        "rj_customer_share_from_sp_sellers": round(float((to_rj["seller_state"] == "SP").mean()), 4),
    }
    return top.round(4).reset_index(), summary


# ----------------------------------------------------------------------------- 4
def controlled_review_effect(d: pd.DataFrame) -> dict:
    x = d[d["low_review"].notna()].copy()
    raw = x.groupby("is_late")["low_review"].mean()

    # (a) Within-seller comparison: compare late vs on-time orders *of the same seller*,
    #     which removes stable seller-level differences (product quality, packaging, listing accuracy).
    g = x.groupby(["seller_id", "is_late"])["low_review"].agg(["mean", "size"]).unstack("is_late")
    g = g.dropna()
    g.columns = [f"{a}_{int(b)}" for a, b in g.columns]
    w = g["size_1"]  # weight by late orders: average effect among late orders
    within = float(((g["mean_1"] - g["mean_0"]) * w).sum() / w.sum())

    # (b) Logistic regression with controls for order value, freight burden, basket size,
    #     route distance proxy (inter/intra-state), customer state, category and month.
    x["log_price"] = np.log(x["product_revenue"].clip(lower=1))
    x["freight_ratio"] = (x["freight_revenue"] / x["product_revenue"]).clip(upper=3)
    x["multi_item"] = (x["item_count"] > 1).astype(int)
    x["interstate"] = (x["seller_state"] != x["customer_state"]).astype(int)
    top_cats = x["category_en"].value_counts().head(30).index
    x["cat"] = np.where(x["category_en"].isin(top_cats), x["category_en"], "other")
    x["month"] = x["purchase_month"].dt.strftime("%Y-%m")
    formula = ("low_review ~ is_late + log_price + freight_ratio + multi_item + interstate"
               " + C(customer_state) + C(cat) + C(month)")
    # Orders from the same seller are not independent -> cluster-robust standard errors by seller.
    x["seller_code"] = x["seller_id"].astype("category").cat.codes
    m = smf.logit(formula, data=x).fit(disp=False, maxiter=200, cov_type="cluster",
                                       cov_kwds={"groups": x["seller_code"]})
    ci = m.conf_int().loc["is_late"]
    ame = m.get_margeff(at="overall", dummy=True).summary_frame().loc["is_late"]  # discrete 0->1 change

    # (c) Dose-response: low-review rate by days late (already in SQL q07) -> monotonic check
    dr = (x[x["is_late"] == 1].assign(b=pd.cut(x["days_vs_estimate"], [0, 3, 7, 14, 1000]))
          .groupby("b", observed=True)["low_review"].mean().round(4))
    return {
        "n_orders": int(len(x)),
        "raw_low_review_rate_on_time": round(float(raw.loc[0]), 4),
        "raw_low_review_rate_late": round(float(raw.loc[1]), 4),
        "raw_gap_pp": round(float(raw.loc[1] - raw.loc[0]) * 100, 1),
        "within_seller_sellers_used": int(len(g)),
        "within_seller_late_orders_covered": int(w.sum()),
        "within_seller_gap_pp": round(within * 100, 1),
        "logit_odds_ratio_late": round(float(np.exp(m.params["is_late"])), 2),
        "logit_odds_ratio_ci95": [round(float(np.exp(ci[0])), 2), round(float(np.exp(ci[1])), 2)],
        "logit_avg_marginal_effect_pp": round(float(ame["dy/dx"]) * 100, 1),
        "logit_ame_ci95_pp": [round(float(ame["Conf. Int. Low"]) * 100, 1), round(float(ame["Cont. Int. Hi."]) * 100, 1)],
        "logit_pseudo_r2": round(float(m.prsquared), 4),
        "logit_controls": formula,
        "logit_standard_errors": "cluster-robust by seller",
        "dose_response_low_review_by_days_late": {str(k): v for k, v in dr.items()},
    }


# ----------------------------------------------------------------------------- 5
def estimate_backtest(d: pd.DataFrame, quantiles=tuple(np.round(np.arange(0.80, 0.971, 0.01), 2))) -> pd.DataFrame:
    """Out-of-sample test of route-calibrated delivery promises.

    Train: orders purchased in 2017. Test: Jan-Aug 2018.
    For each route the promise = ceil(quantile of whole-day delivery time in train);
    fallback to customer-state quantile, then global, when a route has < MIN_ROUTE_ORDERS.
    'Late' is recomputed as actual whole days > promised days (same rule as the platform metric).
    """
    train = d[d["purchase_ts"] < "2018-01-01"]
    test = d[d["purchase_ts"] >= "2018-01-01"].copy()
    rows = [{
        "policy": "Current platform estimate", "quantile": None,
        "late_rate": round(float((test["delivery_days_int"] > test["promised_days"]).mean()), 4),
        "avg_promised_days": round(float(test["promised_days"].mean()), 1),
        "median_promised_days": float(test["promised_days"].median()),
    }]
    for q in quantiles:
        rq = train.groupby("route")["delivery_days_int"].agg(["size", lambda s: s.quantile(q)])
        rq.columns = ["n", "p"]
        sq = train.groupby("customer_state")["delivery_days_int"].quantile(q)
        gq = train["delivery_days_int"].quantile(q)
        route_p = test["route"].map(rq.loc[rq["n"] >= MIN_ROUTE_ORDERS, "p"])
        promise = np.ceil(route_p.fillna(test["customer_state"].map(sq)).fillna(gq))
        rows.append({
            "policy": f"Route-calibrated P{int(q * 100)}", "quantile": q,
            "late_rate": round(float((test["delivery_days_int"] > promise).mean()), 4),
            "avg_promised_days": round(float(promise.mean()), 1),
            "median_promised_days": float(promise.median()),
        })
    out = pd.DataFrame(rows)
    # Like-for-like comparison: the route policy whose average promise is closest to today's.
    cur_days = out.loc[0, "avg_promised_days"]
    cand = out.iloc[1:]
    matched = cand.loc[(cand["avg_promised_days"] - cur_days).abs().idxmin()]
    out["is_matched_to_current_avg_promise"] = out.index == matched.name
    out["test_orders"] = len(test)
    return out


# ----------------------------------------------------------------------------- 6
def distance_matched_lanes(d: pd.DataFrame, lanes: list[str], bin_km: int = 50) -> pd.DataFrame:
    """Is a lane late because it is long, or for lane-specific reasons?

    For each lane, expected late rate = late rate of *other* lanes' orders in the same 50 km
    distance bins, weighted by the lane's own distance mix (direct standardisation).
    """
    from .stats import haversine_km
    g = load_processed("geo_zip").set_index("zip_prefix")[["latitude", "longitude"]]
    s_zip = load_processed("sellers").set_index("seller_id")["zip_prefix"]
    c_zip = load_processed("customers").set_index("customer_id")["zip_prefix"]
    x = d.assign(s_zip=d["seller_id"].map(s_zip), c_zip=d["customer_id"].map(c_zip))
    x = (x.join(g.add_prefix("s_"), on="s_zip").join(g.add_prefix("c_"), on="c_zip")
          .dropna(subset=["s_latitude", "c_latitude"]))
    x["km"] = haversine_km(x["s_latitude"], x["s_longitude"], x["c_latitude"], x["c_longitude"])
    x["bin"] = (x["km"] // bin_km).astype(int)
    rows = []
    for lane in lanes:
        own = x[x["route"] == lane]
        ref = x[x["route"] != lane].groupby("bin")["is_late"].mean()
        w = own["bin"].value_counts()
        expected = float((w * ref.reindex(w.index)).sum() / w.sum())
        rows.append({"route": lane, "orders": len(own), "median_km": round(float(own["km"].median())),
                     "actual_late_rate": round(float(own["is_late"].mean()), 4),
                     "distance_matched_expected": round(expected, 4),
                     "ratio_actual_to_expected": round(float(own["is_late"].mean()) / expected, 2)})
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------------- 7
def lane_persistence(d: pd.DataFrame, min_orders: int = MIN_ROUTE_ORDERS) -> tuple[pd.DataFrame, dict]:
    """Guard against regression to the mean: lanes are selected as 'bad' on the same data used
    to measure them. Check whether lane late rates in 2017 predict lane late rates in 2018."""
    from scipy.stats import spearmanr
    d = d.assign(year=d["purchase_ts"].dt.year)
    t = d.pivot_table(index="route", columns="year", values="is_late", aggfunc=["mean", "size"])
    t.columns = [f"{a}_{b}" for a, b in t.columns]
    t = t[(t["size_2017"] >= min_orders) & (t["size_2018"] >= min_orders)].copy()
    rho, p = spearmanr(t["mean_2017"], t["mean_2018"])
    base17, base18 = d.loc[d["year"] == 2017, "is_late"].mean(), d.loc[d["year"] == 2018, "is_late"].mean()
    t["excess_ratio_2017"] = t["mean_2017"] / base17
    t["excess_ratio_2018"] = t["mean_2018"] / base18
    top10_2017 = t.sort_values("mean_2017", ascending=False).head(10).index
    summary = {
        "lanes_with_min_orders_both_years": int(len(t)),
        "spearman_lane_late_rate_2017_vs_2018": round(float(rho), 3), "p_value": float(p),
        "platform_late_rate_2017": round(float(base17), 4), "platform_late_rate_2018": round(float(base18), 4),
        "top10_lanes_2017_share_above_platform_in_2018": round(float((t.loc[top10_2017, "excess_ratio_2018"] > 1).mean()), 3),
        "sp_rj_ratio_to_platform_2017": round(float(t.loc["SP->RJ", "excess_ratio_2017"]), 2),
        "sp_rj_ratio_to_platform_2018": round(float(t.loc["SP->RJ", "excess_ratio_2018"]), 2),
    }
    return t.round(4).reset_index(), summary


# ----------------------------------------------------------------------------- run
def run() -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    d = delivered_with_seller()
    decomp = decompose_late_orders(d)
    sellers, s_sum = seller_concentration(d)
    routes, r_sum = route_concentration(d)
    review = controlled_review_effect(d)
    bt = estimate_backtest(d)
    dm = distance_matched_lanes(d, routes["route"].head(10).tolist() + ["SP->MG", "SP->SP"])
    dm.to_csv(OUT / "lane_distance_matched.csv", index=False)
    persist, p_sum = lane_persistence(d)
    persist.to_csv(OUT / "lane_persistence.csv", index=False)
    decomp.to_csv(OUT / "late_decomposition.csv", index=False)
    sellers.to_csv(OUT / "top_sellers_excess_late.csv", index=False)
    routes.to_csv(OUT / "top_routes_excess_late.csv", index=False)
    bt.to_csv(OUT / "estimate_backtest.csv", index=False)
    summary = {
        "coverage": {"delivered_single_seller_orders": int(len(d)),
                     "share_of_delivered_in_window": round(len(d) / len(fulfilment_scope(load_processed("order_summary"))), 4)},
        "seller_concentration": s_sum, "route_concentration": r_sum,
        "controlled_review_effect": review,
        "lane_persistence": p_sum,
    }
    (OUT / "root_cause_summary.json").write_text(json.dumps(summary, indent=2, default=str))
    return {"summary": summary, "decomposition": decomp, "backtest": bt}


if __name__ == "__main__":
    r = run()
    pd.set_option("display.width", 200)
    print(r["decomposition"].to_string(index=False))
    print(r["backtest"].to_string(index=False))
    print(json.dumps(r["summary"], indent=2, default=str))
