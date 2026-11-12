"""KPI calculations on the order-summary table (one row per order).

Definitions match docs/05_kpi_dictionary.md and sql/analysis.sql (q01, q02, q07, q12, q14).
Every function is pure (DataFrame in -> value/DataFrame out) so it can be unit-tested.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

LATENESS_BUCKETS = [
    (-np.inf, -15, "1. 15+ days early"),
    (-14, -8, "2. 8-14 days early"),
    (-7, -1, "3. 1-7 days early"),
    (0, 0, "4. On estimated day"),
    (1, 3, "5. 1-3 days late"),
    (4, 7, "6. 4-7 days late"),
    (8, np.inf, "7. 8+ days late"),
]


# ----------------------------------------------------------------------------- scopes
def revenue_scope(o: pd.DataFrame) -> pd.DataFrame:
    """Orders in the analysis window, excluding canceled/unavailable."""
    return o[(o["in_window"] == 1) & (o["is_revenue_order"] == 1)]


def fulfilment_scope(o: pd.DataFrame) -> pd.DataFrame:
    """Delivered orders (with a delivery timestamp) in the analysis window."""
    return o[(o["in_window"] == 1) & (o["is_delivered"] == 1)]


# ----------------------------------------------------------------------------- KPIs
def kpi_scorecard(o: pd.DataFrame) -> dict[str, float]:
    w = o[o["in_window"] == 1]
    rev, dlv = revenue_scope(o), fulfilment_scope(o)
    reviewed = w[w["review_score"].notna()]
    return {
        "revenue_orders": int(len(rev)),
        "product_revenue": round(float(rev["product_revenue"].sum()), 2),
        "freight_revenue": round(float(rev["freight_revenue"].sum()), 2),
        "avg_order_value": round(float(rev["product_revenue"].sum() / len(rev)), 2),
        "items_per_order": round(float(rev["item_count"].sum() / len(rev)), 3),
        "unique_customers": int(rev["customer_unique_id"].nunique()),
        "freight_to_price_ratio": round(float(rev["freight_revenue"].sum() / rev["product_revenue"].sum()), 4),
        "cancel_unavailable_rate": round(float((w["is_revenue_order"] == 0).mean()), 4),
        "on_time_delivery_rate": round(float(1 - dlv["is_late"].mean()), 4),
        "avg_delivery_days": round(float(dlv["delivery_days"].mean()), 2),
        "avg_review_score_delivered": round(float(dlv["review_score"].dropna().mean()), 3),
        "low_review_rate": round(float((reviewed["review_score"] <= 2).mean()), 4),
    }


def monthly_trend(o: pd.DataFrame) -> pd.DataFrame:
    rev = revenue_scope(o)
    m = (rev.groupby("purchase_month")
            .agg(orders=("order_id", "size"), customers=("customer_unique_id", "nunique"),
                 product_revenue=("product_revenue", "sum"), freight_revenue=("freight_revenue", "sum"))
            .sort_index())
    m["aov"] = m["product_revenue"] / m["orders"]
    m["revenue_mom_pct"] = m["product_revenue"].pct_change() * 100
    m["revenue_3m_moving_avg"] = m["product_revenue"].rolling(3, min_periods=1).mean()
    m["cumulative_revenue"] = m["product_revenue"].cumsum()
    return m.reset_index()


def lateness_bucket(days_vs_estimate: pd.Series) -> pd.Series:
    out = pd.Series(pd.NA, index=days_vs_estimate.index, dtype="object")
    for lo, hi, label in LATENESS_BUCKETS:
        out[(days_vs_estimate >= lo) & (days_vs_estimate <= hi)] = label
    return out


def delivery_vs_review(o: pd.DataFrame) -> pd.DataFrame:
    d = fulfilment_scope(o)
    d = d[d["review_score"].notna()].assign(bucket=lambda x: lateness_bucket(x["days_vs_estimate"]))
    return (d.groupby("bucket")
              .agg(orders=("order_id", "size"), avg_review=("review_score", "mean"),
                   low_review_rate=("review_score", lambda s: (s <= 2).mean()),
                   five_star_rate=("review_score", lambda s: (s == 5).mean()))
              .reset_index().rename(columns={"bucket": "delivery_vs_estimate"}))


def customer_frequency(o: pd.DataFrame) -> pd.DataFrame:
    c = revenue_scope(o).groupby("customer_unique_id").agg(orders=("order_id", "size"),
                                                           revenue=("product_revenue", "sum"))
    c["frequency_band"] = np.select([c["orders"] == 1, c["orders"] == 2], ["1 order", "2 orders"], "3+ orders")
    g = c.groupby("frequency_band").agg(customers=("orders", "size"), revenue=("revenue", "sum"))
    g["customer_share_pct"] = 100 * g["customers"] / g["customers"].sum()
    g["revenue_share_pct"] = 100 * g["revenue"] / g["revenue"].sum()
    return g.reset_index()


def repeat_rate(o: pd.DataFrame) -> float:
    """Share of customers (customer_unique_id) with 2+ revenue orders in the window."""
    n = revenue_scope(o).groupby("customer_unique_id").size()
    return float((n > 1).mean())


def first_order_cohort(o: pd.DataFrame, cutoff: str = "2018-06-01") -> pd.DataFrame:
    """Customer-level table: first-order lateness and whether the customer ever reordered.

    Only customers whose first order was placed before `cutoff` are kept so that each has
    at least ~3 months of observable time in which to place a repeat order.
    """
    rev = revenue_scope(o).sort_values(["customer_unique_id", "purchase_ts", "order_id"])
    total = rev.groupby("customer_unique_id").size().rename("total_orders")
    first = rev.drop_duplicates("customer_unique_id", keep="first").set_index("customer_unique_id")
    first = first.join(total)
    first = first[first["is_late"].notna() & (first["purchase_ts"] < pd.Timestamp(cutoff))]
    first["repeated"] = (first["total_orders"] > 1).astype(int)
    return first[["is_late", "review_score", "repeated", "purchase_ts"]].reset_index()


def pareto_share(values: pd.Series, top_fraction: float) -> float:
    """Share of the total contributed by the top `top_fraction` of entities."""
    v = values.sort_values(ascending=False)
    k = max(1, int(np.ceil(len(v) * top_fraction)))
    return float(v.iloc[:k].sum() / v.sum())
