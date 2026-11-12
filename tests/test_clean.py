"""Unit tests for cleaning rules (docs/04_data_cleaning_log.md)."""
import math

import pandas as pd
import pytest

from olist_ba import clean


def test_zip_prefix_restores_leading_zeros():
    assert clean.zip5(pd.Series(["1001", "22000", " 3005"])).tolist() == ["01001", "22000", "03005"]


def test_city_normalisation_strips_accents_and_case(raw_customers):
    c = clean.clean_customers(raw_customers)
    assert c["city"].tolist()[:2] == ["sao paulo", "rio de janeiro"]
    assert c["state"].tolist()[1] == "RJ"


def test_categories_add_missing_translations_once():
    t = pd.DataFrame({"product_category_name": ["beleza_saude", "pc_gamer"],
                      "product_category_name_english": ["health_beauty", "pc_gamer"]})
    c = clean.clean_categories(t)
    assert c["category_pt"].is_unique
    assert {"unknown", "portateis_cozinha_e_preparadores_de_alimentos"} <= set(c["category_pt"])
    assert not c.loc[c["category_pt"] == "unknown", "is_translated_in_source"].iloc[0]


def test_products_null_category_becomes_unknown():
    raw = pd.DataFrame({"product_id": ["p1"], "product_category_name": [None], "product_name_lenght": ["10"],
                        "product_description_lenght": ["100"], "product_photos_qty": ["1"], "product_weight_g": ["500"],
                        "product_length_cm": ["10"], "product_height_cm": ["5"], "product_width_cm": ["5"]})
    p = clean.clean_products(raw)
    assert p.loc[0, "category_pt"] == "unknown"
    assert "name_length" in p.columns  # source typo "lenght" fixed


def test_orders_status_normalised_and_unknown_status_rejected(raw_orders):
    o = clean.clean_orders(raw_orders)
    assert o.loc[4, "order_status"] == "delivered"
    bad = raw_orders.copy()
    bad.loc[0, "order_status"] = "teleported"
    with pytest.raises(ValueError):
        clean.clean_orders(bad)


def test_data_quality_flags(raw_orders):
    o = clean.clean_orders(raw_orders).set_index("order_id")
    assert bool(o.loc["o4", "dq_carrier_before_approval"])          # carrier 08:30 < approval 09:00
    assert bool(o.loc["o3", "dq_status_date_conflict"])             # canceled but has delivery date
    assert bool(o.loc["o5", "dq_status_date_conflict"])             # delivered but no delivery date
    assert not bool(o.loc["o1", "dq_status_date_conflict"])


def test_latest_review_kept_per_order(raw_reviews):
    r = clean.latest_review(clean.clean_reviews(raw_reviews)).set_index("order_id")
    assert r.loc["o1", "review_score"] == 2
    assert len(r) == 2


def test_review_text_flags_treat_whitespace_as_empty(raw_reviews):
    r = clean.clean_reviews(raw_reviews)
    assert r["has_title"].tolist() == [False, False, True]


def test_order_summary_metrics(order_summary):
    s = order_summary.set_index("order_id")
    assert s.loc["o1", "product_revenue"] == pytest.approx(150.50)
    assert s.loc["o1", "freight_revenue"] == pytest.approx(15.25)
    assert s.loc["o1", "item_count"] == 2 and s.loc["o1", "seller_count"] == 2
    assert s.loc["o1", "payment_total"] == pytest.approx(165.75)
    assert s.loc["o1", "delivery_days"] == pytest.approx(5.0)
    assert s.loc["o1", "is_late"] == 0 and s.loc["o2", "is_late"] == 1
    assert s.loc["o2", "days_vs_estimate"] == 5
    assert s.loc["o2", "seller_shipped_late"] == 1              # carrier 03-10 > limit 03-08
    assert s.loc["o1", "promised_days"] == 19
    assert s.loc["o3", "is_revenue_order"] == 0 and s.loc["o3", "item_count"] == 0
    assert s.loc["o4", "in_window"] == 0                         # 2016
    assert s.loc["o5", "in_window"] == 1                         # 2018-08-31 23:00 is inside
    assert math.isnan(s.loc["o5", "is_late"])                    # not delivered -> unknown, not on time
    assert s.loc["o5", "is_delivered"] == 0
    assert s.loc["o1", "review_score"] == 2                      # latest review
