"""Statistical tests behind the headline insights. Writes outputs/stats/stats_summary.json.

Methods are chosen to match the data, not to add complexity:
  * Review scores are ordinal 1-5 -> Mann-Whitney U with rank-biserial effect size.
  * Repeat purchase is binary -> chi-square test of independence + Wilson 95% CIs.
  * Distance vs delivery time is monotonic but skewed -> Spearman rank correlation.
All results are associations in observational data, not causal effects.

Usage: python -m olist_ba.stats
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
from scipy import stats as st

from .clean import load_processed
from .config import OUTPUTS
from .kpis import first_order_cohort, fulfilment_scope, revenue_scope


def wilson_ci(successes: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    p = successes / n
    denom = 1 + z**2 / n
    centre = (p + z**2 / (2 * n)) / denom
    half = z * np.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / denom
    return (round(float(centre - half), 4), round(float(centre + half), 4))


def haversine_km(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(np.radians, (lat1, lon1, lat2, lon2))
    a = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    return 6371.0 * 2 * np.arcsin(np.sqrt(a))


def late_vs_review(o: pd.DataFrame) -> dict:
    d = fulfilment_scope(o)
    d = d[d["review_score"].notna()]
    late, ontime = d.loc[d["is_late"] == 1, "review_score"], d.loc[d["is_late"] == 0, "review_score"]
    u, p = st.mannwhitneyu(late, ontime, alternative="two-sided")
    rbc = 1 - 2 * u / (len(late) * len(ontime))  # rank-biserial (U is for the late group): positive => late scores lower
    low_late, low_on = float((late <= 2).mean()), float((ontime <= 2).mean())
    n_late = int(len(late))
    return {
        "n_late": n_late, "n_on_time": int(len(ontime)),
        "mean_review_late": round(float(late.mean()), 3), "mean_review_on_time": round(float(ontime.mean()), 3),
        "low_review_rate_late": round(low_late, 4), "low_review_rate_on_time": round(low_on, 4),
        "low_review_rate_late_ci95": wilson_ci(int((late <= 2).sum()), n_late),
        "low_review_rate_on_time_ci95": wilson_ci(int((ontime <= 2).sum()), int(len(ontime))),
        "mann_whitney_u": float(u), "p_value": float(p), "rank_biserial": round(float(rbc), 4),
        # Associational estimate: low reviews among late orders above the on-time baseline.
        "excess_low_reviews_among_late": int(round(n_late * (low_late - low_on))),
        "share_of_all_low_reviews_from_late_orders": round(
            float((late <= 2).sum() / ((late <= 2).sum() + (ontime <= 2).sum())), 4),
    }


def late_first_order_vs_repeat(o: pd.DataFrame) -> dict:
    c = first_order_cohort(o)
    g = c.groupby("is_late")["repeated"].agg(["sum", "count"])
    table = np.array([[g.loc[1, "sum"], g.loc[1, "count"] - g.loc[1, "sum"]],
                      [g.loc[0, "sum"], g.loc[0, "count"] - g.loc[0, "sum"]]])
    chi2, p, _, _ = st.chi2_contingency(table)
    r_late, r_on = g.loc[1, "sum"] / g.loc[1, "count"], g.loc[0, "sum"] / g.loc[0, "count"]
    return {
        "customers_first_late": int(g.loc[1, "count"]), "customers_first_on_time": int(g.loc[0, "count"]),
        "repeat_rate_first_late": round(float(r_late), 4), "repeat_rate_first_on_time": round(float(r_on), 4),
        "repeat_rate_first_late_ci95": wilson_ci(int(g.loc[1, "sum"]), int(g.loc[1, "count"])),
        "repeat_rate_first_on_time_ci95": wilson_ci(int(g.loc[0, "sum"]), int(g.loc[0, "count"])),
        "relative_difference": round(float(r_late / r_on - 1), 4),
        "chi2": round(float(chi2), 3), "p_value": float(p),
        "implied_missing_repeat_customers": int(round(g.loc[1, "count"] * (r_on - r_late))),
    }


def distance_vs_delivery(o: pd.DataFrame, items: pd.DataFrame, sellers: pd.DataFrame,
                         customers: pd.DataFrame, geo: pd.DataFrame) -> dict:
    d = fulfilment_scope(o)
    d = d[d["seller_count"] == 1]  # unambiguous origin
    first_seller = items.drop_duplicates("order_id")[["order_id", "seller_id"]]
    g = geo.set_index("zip_prefix")[["latitude", "longitude"]]
    x = (d[["order_id", "customer_id", "delivery_days", "is_late", "freight_revenue", "product_revenue"]]
         .merge(first_seller, on="order_id")
         .merge(sellers[["seller_id", "zip_prefix"]].rename(columns={"zip_prefix": "s_zip"}), on="seller_id")
         .merge(customers[["customer_id", "zip_prefix"]].rename(columns={"zip_prefix": "c_zip"}), on="customer_id")
         .join(g.add_prefix("s_"), on="s_zip").join(g.add_prefix("c_"), on="c_zip")
         .dropna(subset=["s_latitude", "c_latitude"]))
    x["distance_km"] = haversine_km(x["s_latitude"], x["s_longitude"], x["c_latitude"], x["c_longitude"])
    rho_d, p_d = st.spearmanr(x["distance_km"], x["delivery_days"])
    rho_f, p_f = st.spearmanr(x["distance_km"], x["freight_revenue"] / x["product_revenue"])
    bands = pd.cut(x["distance_km"], [-0.1, 100, 500, 1000, 2000, np.inf],
                   labels=["<100 km", "100-500 km", "500-1,000 km", "1,000-2,000 km", "2,000+ km"])
    by_band = (x.groupby(bands, observed=True)
                .agg(orders=("order_id", "size"), median_delivery_days=("delivery_days", "median"),
                     late_rate=("is_late", "mean"))
                .round(4).reset_index().rename(columns={"distance_km": "distance_band"}))
    by_band["distance_band"] = by_band["distance_band"].astype(str)
    x[["distance_km", "delivery_days", "is_late"]].to_parquet(OUTPUTS / "stats" / "distance_sample.parquet")
    return {
        "n_orders": int(len(x)),
        "coverage_of_single_seller_delivered": round(len(x) / len(d), 4),
        "spearman_distance_delivery_days": round(float(rho_d), 4), "p_value_delivery": float(p_d),
        "spearman_distance_freight_ratio": round(float(rho_f), 4), "p_value_freight": float(p_f),
        "by_distance_band": by_band.to_dict(orient="records"),
    }


def late_root_cause(o: pd.DataFrame) -> dict:
    d = fulfilment_scope(o)
    late = d[d["is_late"] == 1]
    known = late[late["seller_shipped_late"].notna()]
    return {
        "late_orders": int(len(late)),
        "share_late_with_seller_sla_miss": round(float(known["seller_shipped_late"].mean()), 4),
        "late_rate_seller_sla_miss": round(float(d.loc[d["seller_shipped_late"] == 1, "is_late"].mean()), 4),
        "late_rate_seller_within_sla": round(float(d.loc[d["seller_shipped_late"] == 0, "is_late"].mean()), 4),
    }


def state_comparison(o: pd.DataFrame, a: str = "RJ", b: str = "SP") -> dict:
    d = fulfilment_scope(o)
    out = {}
    for s in (a, b):
        x = d[d["customer_state"] == s]
        out[s] = {"delivered": int(len(x)), "late_rate": round(float(x["is_late"].mean()), 4),
                  "late_rate_ci95": wilson_ci(int(x["is_late"].sum()), int(len(x))),
                  "avg_review": round(float(x["review_score"].mean()), 3)}
    xa, xb = d[d["customer_state"] == a]["is_late"], d[d["customer_state"] == b]["is_late"]
    table = np.array([[xa.sum(), len(xa) - xa.sum()], [xb.sum(), len(xb) - xb.sum()]])
    chi2, p, _, _ = st.chi2_contingency(table)
    out["chi2"], out["p_value"] = round(float(chi2), 2), float(p)
    rev = revenue_scope(o)
    out[f"{a}_revenue_share"] = round(float(rev.loc[rev["customer_state"] == a, "product_revenue"].sum()
                                            / rev["product_revenue"].sum()), 4)
    return out


def run() -> dict:
    (OUTPUTS / "stats").mkdir(parents=True, exist_ok=True)
    o = load_processed("order_summary")
    res = {
        "late_delivery_vs_review": late_vs_review(o),
        "late_first_order_vs_repeat": late_first_order_vs_repeat(o),
        "distance_vs_delivery": distance_vs_delivery(o, load_processed("order_items"), load_processed("sellers"),
                                                     load_processed("customers"), load_processed("geo_zip")),
        "late_root_cause": late_root_cause(o),
        "rj_vs_sp": state_comparison(o),
    }
    (OUTPUTS / "stats" / "stats_summary.json").write_text(json.dumps(res, indent=2, default=str))
    return res


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, default=str))
