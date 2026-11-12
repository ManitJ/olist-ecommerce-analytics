"""Export a star schema for Power BI (and the Streamlit preview) to data/bi/*.csv.

Tables
  fact_orders        one row per order (all statuses; filter with flags)
  fact_order_items   one row per order item (category / seller revenue)
  dim_date           calendar 2016-09-01 .. 2018-10-31
  dim_geography      27 Brazilian states with official IBGE macro-region
  dim_seller         seller attributes + delivery scorecard (window)
  dim_product        product -> English category
  dim_route          seller-state -> customer-state lanes, target-lane flag
  scenario_results   python scenario output (for the scenario page)

fact_orders carries the per-order lever shares (lever_l1/l2/l4_share) used by the
scenario model so the Power BI what-if measures reproduce python/olist_ba/scenarios.py.

Usage: python -m olist_ba.export_bi
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from .clean import load_processed
from .config import DATA_BI, OUTPUTS
from .root_cause import PEAK_MONTHS
from .scenarios import ASSUMPTIONS, attributable_shares

# IBGE macro-regions (public, factual mapping)
REGIONS = {
    "North": ["AC", "AP", "AM", "PA", "RO", "RR", "TO"],
    "Northeast": ["AL", "BA", "CE", "MA", "PB", "PE", "PI", "RN", "SE"],
    "Center-West": ["DF", "GO", "MT", "MS"],
    "Southeast": ["ES", "MG", "RJ", "SP"],
    "South": ["PR", "RS", "SC"],
}
STATE_NAMES = {
    "AC": "Acre", "AL": "Alagoas", "AP": "Amapá", "AM": "Amazonas", "BA": "Bahia", "CE": "Ceará",
    "DF": "Distrito Federal", "ES": "Espírito Santo", "GO": "Goiás", "MA": "Maranhão", "MT": "Mato Grosso",
    "MS": "Mato Grosso do Sul", "MG": "Minas Gerais", "PA": "Pará", "PB": "Paraíba", "PR": "Paraná",
    "PE": "Pernambuco", "PI": "Piauí", "RJ": "Rio de Janeiro", "RN": "Rio Grande do Norte",
    "RS": "Rio Grande do Sul", "RO": "Rondônia", "RR": "Roraima", "SC": "Santa Catarina",
    "SP": "São Paulo", "SE": "Sergipe", "TO": "Tocantins",
}


def build() -> dict[str, pd.DataFrame]:
    o = load_processed("order_summary")
    items, sellers = load_processed("order_items"), load_processed("sellers")
    products, cats = load_processed("products"), load_processed("categories")

    # Primary item per order (highest price) -> seller, product, category of the order
    prim = (items.sort_values(["order_id", "price", "order_item_id"], ascending=[True, False, True])
                 .drop_duplicates("order_id")[["order_id", "seller_id", "product_id"]])
    prim = (prim.merge(sellers[["seller_id", "state"]].rename(columns={"state": "seller_state"}), on="seller_id")
                .merge(products[["product_id", "category_pt"]], on="product_id")
                .merge(cats[["category_pt", "category_en"]], on="category_pt"))
    f = o.merge(prim[["order_id", "seller_id", "seller_state", "category_en"]], on="order_id", how="left")
    f["route"] = np.where(f["seller_state"].notna(), f["seller_state"] + "->" + f["customer_state"], None)
    f["is_peak_month"] = f["purchase_month"].isin(PEAK_MONTHS).astype(int)
    f["low_review"] = np.where(f["review_score"].isna(), np.nan, (f["review_score"] <= 2).astype(float))
    f["delivered_date"] = f["delivered_customer_ts"].dt.normalize()

    # Scenario baseline + per-order lever shares (same function as scenarios.py)
    f["is_scenario_baseline"] = ((f["is_delivered"] == 1) & (f["seller_count"] == 1)
                                 & (f["purchase_ts"] >= "2017-09-01") & (f["purchase_ts"] < "2018-09-01")).astype(int)
    base = f[f["is_scenario_baseline"] == 1]
    shares, meta = attributable_shares(base, ASSUMPTIONS["L1_target_lanes"])
    for k in ("L1", "L2", "L4"):
        f[f"lever_{k.lower()}_share"] = 0.0
        f.loc[shares.index, f"lever_{k.lower()}_share"] = shares[k].round(6)

    fact_cols = ["order_id", "customer_unique_id", "customer_state", "seller_id", "seller_state", "route",
                 "category_en", "order_status", "purchase_date", "purchase_month", "delivered_date",
                 "estimated_delivery_date", "in_window", "is_revenue_order", "is_delivered", "is_peak_month",
                 "item_count", "product_revenue", "freight_revenue", "gmv", "payment_total", "max_installments",
                 "approval_hours", "seller_to_carrier_days", "carrier_to_customer_days", "delivery_days",
                 "promised_days", "days_vs_estimate", "is_late", "seller_shipped_late", "review_score", "low_review",
                 "is_scenario_baseline", "lever_l1_share", "lever_l2_share", "lever_l4_share",
                 "dq_carrier_before_approval", "dq_delivered_before_carrier", "dq_status_date_conflict"]
    fact = f[fact_cols].copy()
    for c in ("approval_hours", "seller_to_carrier_days", "carrier_to_customer_days", "delivery_days"):
        fact[c] = fact[c].round(3)

    fi = (items.merge(o[["order_id", "purchase_date", "in_window", "is_revenue_order"]], on="order_id")
               [["order_id", "order_item_id", "product_id", "seller_id", "purchase_date", "in_window",
                 "is_revenue_order", "price", "freight_value"]])

    dates = pd.date_range("2016-09-01", "2018-10-31", freq="D")
    dim_date = pd.DataFrame({"date": dates})
    dim_date["year"] = dim_date["date"].dt.year
    dim_date["quarter"] = "Q" + dim_date["date"].dt.quarter.astype(str)
    dim_date["month_num"] = dim_date["date"].dt.month
    dim_date["month_name"] = dim_date["date"].dt.strftime("%b")
    dim_date["year_month"] = dim_date["date"].dt.strftime("%Y-%m")
    dim_date["month_start"] = dim_date["date"].dt.to_period("M").dt.to_timestamp()
    dim_date["iso_weekday"] = dim_date["date"].dt.isocalendar().day.astype(int)
    dim_date["weekday_name"] = dim_date["date"].dt.strftime("%a")
    dim_date["in_window"] = ((dim_date["date"] >= "2017-01-01") & (dim_date["date"] < "2018-09-01")).astype(int)
    dim_date["is_peak_month"] = dim_date["month_start"].isin(PEAK_MONTHS).astype(int)

    region_of = {s: r for r, ss in REGIONS.items() for s in ss}
    dim_geo = pd.DataFrame({"state": sorted(STATE_NAMES)})
    dim_geo["state_name"] = dim_geo["state"].map(STATE_NAMES)
    dim_geo["region"] = dim_geo["state"].map(region_of)

    w = f[(f["in_window"] == 1) & (f["is_delivered"] == 1)]
    sc = w.groupby("seller_id").agg(delivered_orders=("order_id", "size"), late_rate=("is_late", "mean"),
                                    sla_miss_rate=("seller_shipped_late", "mean"),
                                    low_review_rate=("low_review", "mean")).round(4)
    dim_seller = sellers.rename(columns={"state": "seller_state"}).merge(sc, on="seller_id", how="left")
    dim_seller["delivered_orders"] = dim_seller["delivered_orders"].fillna(0).astype(int)
    eligible = dim_seller["delivered_orders"] >= 30
    dim_seller["seller_tier"] = np.select(
        [~eligible,
         eligible & (dim_seller["sla_miss_rate"] > 0.15) & (dim_seller["late_rate"] > 0.10),
         eligible & ((dim_seller["sla_miss_rate"] > 0.15) | (dim_seller["late_rate"] > 0.10))],
        ["Low volume (<30 orders)", "Intervene", "Monitor"], "Healthy")

    dim_product = products.merge(cats[["category_pt", "category_en"]], on="category_pt")[
        ["product_id", "category_en", "weight_g"]]

    lanes = set(meta["L1_lanes"])
    rt = (w[w["route"].notna()].groupby("route")
           .agg(seller_state=("seller_state", "first"), customer_state=("customer_state", "first"),
                delivered_orders=("order_id", "size"), late_rate=("is_late", "mean")).round(4).reset_index())
    rt["is_target_lane"] = rt["route"].isin(lanes).astype(int)
    all_routes = pd.DataFrame({"route": sorted(f["route"].dropna().unique())})
    dim_route = all_routes.merge(rt, on="route", how="left")
    dim_route["seller_state"] = dim_route["route"].str[:2]
    dim_route["customer_state"] = dim_route["route"].str[-2:]
    dim_route["is_target_lane"] = dim_route["is_target_lane"].fillna(0).astype(int)
    dim_route["delivered_orders"] = dim_route["delivered_orders"].fillna(0).astype(int)

    scen = pd.read_csv(OUTPUTS / "scenarios" / "scenario_results.csv")
    return {"fact_orders": fact, "fact_order_items": fi, "dim_date": dim_date, "dim_geography": dim_geo,
            "dim_seller": dim_seller, "dim_product": dim_product, "dim_route": dim_route,
            "scenario_results": scen}


def main() -> None:
    DATA_BI.mkdir(parents=True, exist_ok=True)
    tables = build()
    for name, df in tables.items():
        df.to_csv(DATA_BI / f"{name}.csv", index=False, date_format="%Y-%m-%d")
        print(f"  {name:<18} {len(df):>8,} rows")
    manifest = {k: {"rows": len(v), "columns": list(v.columns)} for k, v in tables.items()}
    (DATA_BI / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"Wrote {len(tables)} tables to {DATA_BI}")


if __name__ == "__main__":
    main()
