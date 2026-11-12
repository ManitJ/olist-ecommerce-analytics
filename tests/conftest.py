"""Shared fixtures. Unit tests use tiny hand-built frames; integration tests use the real
pipeline outputs and are skipped (not failed) if the pipeline has not been run."""
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))

from olist_ba.config import DATA_BI, DATA_PROCESSED, DUCKDB_PATH, OUTPUTS  # noqa: E402

PIPELINE_READY = (DATA_PROCESSED / "order_summary.parquet").exists() and DUCKDB_PATH.exists() \
    and (OUTPUTS / "key_metrics.json").exists() and (DATA_BI / "fact_orders.csv").exists()

integration = pytest.mark.skipif(not PIPELINE_READY, reason="run `make all` first (pipeline outputs missing)")


@pytest.fixture
def raw_orders() -> pd.DataFrame:
    """Five orders covering on-time, late, canceled, out-of-window and missing-date cases."""
    return pd.DataFrame({
        "order_id": ["o1", "o2", "o3", "o4", "o5"],
        "customer_id": ["c1", "c2", "c3", "c4", "c5"],
        "order_status": ["delivered", "delivered", "canceled", "delivered", "Delivered "],
        "order_purchase_timestamp": ["2017-03-01 10:00:00", "2017-03-05 12:00:00", "2017-04-01 09:00:00",
                                     "2016-10-01 08:00:00", "2018-08-31 23:00:00"],
        "order_approved_at": ["2017-03-01 11:00:00", "2017-03-05 13:00:00", None,
                              "2016-10-01 09:00:00", "2018-09-01 01:00:00"],
        "order_delivered_carrier_date": ["2017-03-02 10:00:00", "2017-03-10 12:00:00", None,
                                         "2016-10-01 08:30:00", None],
        "order_delivered_customer_date": ["2017-03-06 10:00:00", "2017-03-25 12:00:00", "2017-04-09 09:00:00",
                                          "2016-10-11 08:00:00", None],
        "order_estimated_delivery_date": ["2017-03-20 00:00:00", "2017-03-20 00:00:00", "2017-04-20 00:00:00",
                                          "2016-10-20 00:00:00", "2018-09-20 00:00:00"],
    })


@pytest.fixture
def raw_customers() -> pd.DataFrame:
    return pd.DataFrame({
        "customer_id": ["c1", "c2", "c3", "c4", "c5"],
        "customer_unique_id": ["u1", "u1", "u2", "u3", "u4"],
        "customer_zip_code_prefix": ["1001", "22000", "3005", "1001", "99999"],
        "customer_city": ["São Paulo", " rio de janeiro", "Belo Horizonte", "são paulo", "x"],
        "customer_state": ["SP", "rj", "MG", "SP", "RS"],
    })


@pytest.fixture
def raw_items() -> pd.DataFrame:
    return pd.DataFrame({
        "order_id": ["o1", "o1", "o2", "o4"],
        "order_item_id": ["1", "2", "1", "1"],
        "product_id": ["p1", "p2", "p1", "p1"],
        "seller_id": ["s1", "s2", "s1", "s1"],
        "shipping_limit_date": ["2017-03-03 10:00:00", "2017-03-03 10:00:00", "2017-03-08 12:00:00",
                                "2016-10-03 08:00:00"],
        "price": ["100.00", "50.50", "200.00", "10.00"],
        "freight_value": ["10.00", "5.25", "30.00", "0.00"],
    })


@pytest.fixture
def raw_payments() -> pd.DataFrame:
    return pd.DataFrame({
        "order_id": ["o1", "o1", "o2"], "payment_sequential": ["1", "2", "1"],
        "payment_type": ["credit_card", "voucher", "boleto"], "payment_installments": ["3", "1", "1"],
        "payment_value": ["150.00", "15.75", "230.00"],
    })


@pytest.fixture
def raw_reviews() -> pd.DataFrame:
    """o1 has two reviews (latest = score 2); o2 one review."""
    return pd.DataFrame({
        "review_id": ["r1", "r2", "r3"], "order_id": ["o1", "o1", "o2"], "review_score": ["5", "2", "1"],
        "review_comment_title": [None, "  ", "bad"], "review_comment_message": ["ok", None, "late"],
        "review_creation_date": ["2017-03-07 00:00:00", "2017-03-08 00:00:00", "2017-03-26 00:00:00"],
        "review_answer_timestamp": ["2017-03-07 10:00:00", "2017-03-09 10:00:00", "2017-03-27 10:00:00"],
    })


@pytest.fixture
def order_summary(raw_orders, raw_customers, raw_items, raw_payments, raw_reviews) -> pd.DataFrame:
    from olist_ba import clean
    return clean.build_order_summary(clean.clean_orders(raw_orders), clean.clean_customers(raw_customers),
                                     clean.clean_order_items(raw_items), clean.clean_payments(raw_payments),
                                     clean.clean_reviews(raw_reviews))
