"""Clean raw Olist CSVs with pandas and write typed tables to data/processed/*.parquet.

This is an independent implementation of the rules in sql/load.sql. Keeping two
implementations lets tests/test_reconciliation.py prove that SQL and Python KPIs agree.
Every rule is documented in docs/04_data_cleaning_log.md.

Usage: python -m olist_ba.clean
"""
from __future__ import annotations

import unicodedata

import numpy as np
import pandas as pd

from .config import DATA_PROCESSED, DATA_RAW, RAW_FILES

WINDOW_START = pd.Timestamp("2017-01-01")
WINDOW_END = pd.Timestamp("2018-09-01")  # exclusive
NON_REVENUE_STATUSES = {"canceled", "unavailable"}
VALID_STATUSES = {"created", "approved", "invoiced", "processing", "shipped",
                  "delivered", "canceled", "unavailable"}
EXTRA_TRANSLATIONS = {
    "pc_gamer": "pc_gamer",
    "portateis_cozinha_e_preparadores_de_alimentos": "portable_kitchen_food_preparers",
    "unknown": "unknown",
}
BRAZIL_BBOX = {"lat": (-33.75, 5.27), "lng": (-73.99, -34.79)}


# ----------------------------------------------------------------------------- helpers
def read_raw(name: str) -> pd.DataFrame:
    """Read a raw file as text (mirrors the all-VARCHAR staging layer)."""
    return pd.read_csv(DATA_RAW / RAW_FILES[name], dtype=str, keep_default_na=False, na_values=[""])


def strip_accents(s: pd.Series) -> pd.Series:
    def _f(x: str) -> str:
        return "".join(c for c in unicodedata.normalize("NFKD", x) if not unicodedata.combining(c))
    return s.map(_f, na_action="ignore")


def zip5(s: pd.Series) -> pd.Series:
    return s.str.strip().str.zfill(5)


def _ts(s: pd.Series) -> pd.Series:
    return pd.to_datetime(s, format="%Y-%m-%d %H:%M:%S", errors="raise")


# ----------------------------------------------------------------------------- tables
def clean_categories(translation: pd.DataFrame) -> pd.DataFrame:
    df = pd.DataFrame({
        "category_pt": translation["product_category_name"].str.strip(),
        "category_en": translation["product_category_name_english"].str.strip(),
        "is_translated_in_source": True,
    })
    extra = pd.DataFrame([{"category_pt": k, "category_en": v, "is_translated_in_source": False}
                          for k, v in EXTRA_TRANSLATIONS.items() if k not in set(df["category_pt"])])
    return pd.concat([df, extra], ignore_index=True)


def clean_customers(raw: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame({
        "customer_id": raw["customer_id"],
        "customer_unique_id": raw["customer_unique_id"],
        "zip_prefix": zip5(raw["customer_zip_code_prefix"]),
        "city": strip_accents(raw["customer_city"]).str.strip().str.lower(),
        "state": raw["customer_state"].str.strip().str.upper(),
    })


def clean_sellers(raw: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame({
        "seller_id": raw["seller_id"],
        "zip_prefix": zip5(raw["seller_zip_code_prefix"]),
        "city": strip_accents(raw["seller_city"]).str.strip().str.lower(),
        "state": raw["seller_state"].str.strip().str.upper(),
    })


def clean_products(raw: pd.DataFrame) -> pd.DataFrame:
    cat = raw["product_category_name"].str.strip().replace("", np.nan).fillna("unknown")
    num = {  # source columns contain the typo "lenght"; fixed here
        "name_length": "product_name_lenght", "description_length": "product_description_lenght",
        "photos_qty": "product_photos_qty", "weight_g": "product_weight_g",
        "length_cm": "product_length_cm", "height_cm": "product_height_cm", "width_cm": "product_width_cm",
    }
    out = pd.DataFrame({"product_id": raw["product_id"], "category_pt": cat})
    for new, old in num.items():
        out[new] = pd.to_numeric(raw[old]).astype("Int64")
    return out


def clean_orders(raw: pd.DataFrame) -> pd.DataFrame:
    o = pd.DataFrame({
        "order_id": raw["order_id"],
        "customer_id": raw["customer_id"],
        "order_status": raw["order_status"].str.strip().str.lower(),
        "purchase_ts": _ts(raw["order_purchase_timestamp"]),
        "approved_ts": _ts(raw["order_approved_at"]),
        "delivered_carrier_ts": _ts(raw["order_delivered_carrier_date"]),
        "delivered_customer_ts": _ts(raw["order_delivered_customer_date"]),
        "estimated_delivery_date": _ts(raw["order_estimated_delivery_date"]).dt.normalize(),
    })
    unknown = set(o["order_status"]) - VALID_STATUSES
    if unknown:
        raise ValueError(f"Unexpected order statuses: {unknown}")
    o["dq_carrier_before_approval"] = (o["delivered_carrier_ts"] < o["approved_ts"]).fillna(False)
    o["dq_delivered_before_carrier"] = (o["delivered_customer_ts"] < o["delivered_carrier_ts"]).fillna(False)
    o["dq_status_date_conflict"] = (
        ((o["order_status"] == "delivered") & o["delivered_customer_ts"].isna())
        | ((o["order_status"] == "canceled") & o["delivered_customer_ts"].notna())
    )
    return o


def clean_order_items(raw: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame({
        "order_id": raw["order_id"],
        "order_item_id": raw["order_item_id"].astype(int),
        "product_id": raw["product_id"],
        "seller_id": raw["seller_id"],
        "shipping_limit_ts": _ts(raw["shipping_limit_date"]),
        "price": pd.to_numeric(raw["price"]).round(2),
        "freight_value": pd.to_numeric(raw["freight_value"]).round(2),
    })


def clean_payments(raw: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame({
        "order_id": raw["order_id"],
        "payment_sequential": raw["payment_sequential"].astype(int),
        "payment_type": raw["payment_type"].str.strip().str.lower(),
        "installments": raw["payment_installments"].astype(int),
        "payment_value": pd.to_numeric(raw["payment_value"]).round(2),
    })


def clean_reviews(raw: pd.DataFrame) -> pd.DataFrame:
    def has_text(s: pd.Series) -> pd.Series:
        return s.notna() & (s.fillna("").str.strip() != "")
    return pd.DataFrame({
        "review_id": raw["review_id"],
        "order_id": raw["order_id"],
        "review_score": raw["review_score"].astype(int),
        "has_title": has_text(raw["review_comment_title"]),
        "has_message": has_text(raw["review_comment_message"]),
        "creation_date": _ts(raw["review_creation_date"]).dt.normalize(),
        "answer_ts": _ts(raw["review_answer_timestamp"]),
    })


def clean_geo(raw: pd.DataFrame) -> pd.DataFrame:
    g = pd.DataFrame({
        "zip_prefix": zip5(raw["geolocation_zip_code_prefix"]),
        "latitude": pd.to_numeric(raw["geolocation_lat"]),
        "longitude": pd.to_numeric(raw["geolocation_lng"]),
    })
    g = g[g["latitude"].between(*BRAZIL_BBOX["lat"]) & g["longitude"].between(*BRAZIL_BBOX["lng"])]
    return (g.groupby("zip_prefix", as_index=False)
             .agg(latitude=("latitude", "mean"), longitude=("longitude", "mean"), n_points=("latitude", "size")))


def latest_review(reviews: pd.DataFrame) -> pd.DataFrame:
    """One review per order: latest answer timestamp, review_id as tie-break (matches SQL)."""
    r = reviews.sort_values(["order_id", "answer_ts", "review_id"], ascending=[True, False, True])
    return r.drop_duplicates("order_id", keep="first")[["order_id", "review_score", "has_message"]]


def build_order_summary(orders: pd.DataFrame, customers: pd.DataFrame, items: pd.DataFrame,
                        payments: pd.DataFrame, reviews: pd.DataFrame) -> pd.DataFrame:
    """One row per order; mirrors dw.v_order_summary in sql/load.sql."""
    it = items.groupby("order_id").agg(
        item_count=("order_item_id", "size"), seller_count=("seller_id", "nunique"),
        product_revenue=("price", "sum"), freight_revenue=("freight_value", "sum"),
        shipping_limit_ts=("shipping_limit_ts", "max"))
    pay = payments.groupby("order_id").agg(payment_total=("payment_value", "sum"),
                                           max_installments=("installments", "max"))
    o = (orders.merge(customers[["customer_id", "customer_unique_id", "state"]], on="customer_id", how="inner")
               .rename(columns={"state": "customer_state"})
               .merge(it, on="order_id", how="left")
               .merge(pay, on="order_id", how="left")
               .merge(latest_review(reviews)[["order_id", "review_score"]], on="order_id", how="left"))

    for c in ("item_count", "seller_count"):
        o[c] = o[c].fillna(0).astype(int)
    for c in ("product_revenue", "freight_revenue"):
        o[c] = o[c].fillna(0.0).round(2)
    o["gmv"] = (o["product_revenue"] + o["freight_revenue"]).round(2)

    o["purchase_date"] = o["purchase_ts"].dt.normalize()
    o["purchase_month"] = o["purchase_ts"].dt.to_period("M").dt.to_timestamp()
    o["in_window"] = ((o["purchase_ts"] >= WINDOW_START) & (o["purchase_ts"] < WINDOW_END)).astype(int)
    o["is_revenue_order"] = (~o["order_status"].isin(NON_REVENUE_STATUSES)).astype(int)
    o["is_delivered"] = ((o["order_status"] == "delivered") & o["delivered_customer_ts"].notna()).astype(int)

    secs = lambda a, b: (o[b] - o[a]).dt.total_seconds()  # noqa: E731
    o["approval_hours"] = secs("purchase_ts", "approved_ts") / 3600
    o["seller_to_carrier_days"] = secs("approved_ts", "delivered_carrier_ts") / 86400
    o["carrier_to_customer_days"] = secs("delivered_carrier_ts", "delivered_customer_ts") / 86400
    o["delivery_days"] = secs("purchase_ts", "delivered_customer_ts") / 86400
    o["days_vs_estimate"] = (o["delivered_customer_ts"].dt.normalize() - o["estimated_delivery_date"]).dt.days
    o["is_late"] = np.where(o["delivered_customer_ts"].isna(), np.nan,
                            (o["delivered_customer_ts"].dt.normalize() > o["estimated_delivery_date"]).astype(float))
    o["seller_shipped_late"] = np.where(o["delivered_carrier_ts"].isna() | o["shipping_limit_ts"].isna(), np.nan,
                                        (o["delivered_carrier_ts"] > o["shipping_limit_ts"]).astype(float))
    o["promised_days"] = (o["estimated_delivery_date"] - o["purchase_date"]).dt.days
    return o.drop(columns=["shipping_limit_ts"])


# ----------------------------------------------------------------------------- run
def build_all() -> dict[str, pd.DataFrame]:
    t = {
        "categories": clean_categories(read_raw("category_translation")),
        "customers": clean_customers(read_raw("customers")),
        "sellers": clean_sellers(read_raw("sellers")),
        "products": clean_products(read_raw("products")),
        "orders": clean_orders(read_raw("orders")),
        "order_items": clean_order_items(read_raw("order_items")),
        "payments": clean_payments(read_raw("payments")),
        "reviews": clean_reviews(read_raw("reviews")),
        "geo_zip": clean_geo(read_raw("geolocation")),
    }
    t["order_summary"] = build_order_summary(t["orders"], t["customers"], t["order_items"],
                                             t["payments"], t["reviews"])
    return t


def load_processed(name: str) -> pd.DataFrame:
    return pd.read_parquet(DATA_PROCESSED / f"{name}.parquet")


def main() -> None:
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    tables = build_all()
    for name, df in tables.items():
        df.to_parquet(DATA_PROCESSED / f"{name}.parquet", index=False)
        print(f"  {name:<14} {len(df):>9,} rows")
    print(f"Wrote {len(tables)} tables to {DATA_PROCESSED}")


if __name__ == "__main__":
    main()
