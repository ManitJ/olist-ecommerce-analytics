"""Integration: the SQL (DuckDB) layer and the independent pandas layer must agree exactly."""
import json

import numpy as np
import pandas as pd
import pytest

from conftest import integration
from olist_ba import kpis
from olist_ba.clean import load_processed
from olist_ba.config import OUTPUTS, SQL_DIR
from olist_ba.run_sql import connect, run_named

pytestmark = integration


@pytest.fixture(scope="module")
def con():
    c = connect(read_only=True)
    yield c
    c.close()


@pytest.fixture(scope="module")
def pandas_summary():
    return load_processed("order_summary").set_index("order_id").sort_index()


def test_all_validation_checks_pass(con):
    for name, df in run_named(con, SQL_DIR / "validation.sql").items():
        assert not (df["status"] == "FAIL").any(), f"{name} failed:\n{df}"


def test_order_summary_sql_equals_pandas_every_column(con, pandas_summary):
    v = con.execute("SELECT * FROM dw.v_order_summary").df().set_index("order_id").sort_index()
    assert len(v) == len(pandas_summary) == 99441
    for c in v.columns:
        a, b = v[c], pandas_summary[c]
        if c.endswith(("_ts", "_date", "_month")):
            a, b = pd.to_datetime(a), pd.to_datetime(b)
            same = (a == b) | (a.isna() & b.isna())
        elif pd.api.types.is_numeric_dtype(a) or a.dtype == bool:
            a = pd.to_numeric(a.astype("float64"), errors="coerce")
            b = pd.to_numeric(b.astype("float64"), errors="coerce")
            same = np.isclose(a, b, atol=1e-6) | (a.isna() & b.isna())
        else:
            same = a.astype(str) == b.astype(str)
        assert same.all(), f"column {c}: {(~same).sum()} mismatches"


def test_headline_kpis_sql_equals_pandas(pandas_summary):
    sql = pd.read_csv(OUTPUTS / "sql" / "analysis" / "q01_kpi_scorecard.csv").iloc[0]
    py = kpis.kpi_scorecard(pandas_summary.reset_index())
    for k, v in py.items():
        assert v == pytest.approx(sql[k], abs=1e-9), k


def test_monthly_trend_sql_equals_pandas(pandas_summary):
    sql = pd.read_csv(OUTPUTS / "sql" / "analysis" / "q02_monthly_revenue_trend.csv")
    py = kpis.monthly_trend(pandas_summary.reset_index())
    assert len(sql) == len(py) == 20
    np.testing.assert_allclose(sql["product_revenue"], py["product_revenue"].round(2), atol=0.005)
    np.testing.assert_array_equal(sql["orders"], py["orders"])
    np.testing.assert_allclose(sql["cumulative_revenue"], py["cumulative_revenue"].round(2), atol=0.01)


def test_delivery_review_buckets_sql_equals_pandas(pandas_summary):
    sql = pd.read_csv(OUTPUTS / "sql" / "analysis" / "q07_delivery_vs_review.csv")
    py = kpis.delivery_vs_review(pandas_summary.reset_index())
    m = sql.merge(py, on="delivery_vs_estimate", suffixes=("_sql", "_py"))
    assert len(m) == 7
    np.testing.assert_array_equal(m["orders_sql"], m["orders_py"])
    np.testing.assert_allclose(m["avg_review_sql"], m["avg_review_py"].round(2), atol=0.005)


def test_customer_frequency_sql_equals_pandas(pandas_summary):
    sql = pd.read_csv(OUTPUTS / "sql" / "analysis" / "q12_customer_frequency.csv").set_index("frequency_band")
    py = kpis.customer_frequency(pandas_summary.reset_index()).set_index("frequency_band")
    np.testing.assert_array_equal(sql["customers"], py.loc[sql.index, "customers"])


def test_first_order_repeat_sql_equals_pandas(pandas_summary):
    sql = pd.read_csv(OUTPUTS / "sql" / "analysis" / "q14_first_delivery_vs_repeat.csv")
    py = kpis.first_order_cohort(pandas_summary.reset_index())
    late_sql = sql.set_index("first_order_experience").loc["First order late"]
    assert late_sql["customers"] == (py["is_late"] == 1).sum()
    assert late_sql["repeat_customers"] == py.loc[py["is_late"] == 1, "repeated"].sum()


def test_key_metrics_consistent_with_sources():
    km = json.loads((OUTPUTS / "key_metrics.json").read_text())
    assert km["share_late_post_handoff"] + km["share_late_seller_sla_miss"] == pytest.approx(1.0, abs=1e-3)
    assert km["scenario_low_new_late_rate"] > km["scenario_base_new_late_rate"] > km["scenario_high_new_late_rate"]
