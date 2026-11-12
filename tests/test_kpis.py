"""Unit tests for KPI definitions (docs/05_kpi_dictionary.md)."""
import numpy as np
import pandas as pd
import pytest

from olist_ba import kpis


def test_scorecard_scopes(order_summary):
    k = kpis.kpi_scorecard(order_summary)
    # revenue scope: in-window and not canceled -> o1, o2, o5 (o5 has no items)
    assert k["revenue_orders"] == 3
    assert k["product_revenue"] == pytest.approx(350.50)
    assert k["avg_order_value"] == pytest.approx(round(350.50 / 3, 2))
    assert k["unique_customers"] == 2                        # o1 & o2 share customer u1
    # fulfilment scope: delivered in window -> o1 (on time), o2 (late)
    assert k["on_time_delivery_rate"] == pytest.approx(0.5)
    # cancel rate over all in-window orders: o3 of {o1,o2,o3,o5}
    assert k["cancel_unavailable_rate"] == pytest.approx(0.25)


@pytest.mark.parametrize("days,label", [(-15, "1. 15+ days early"), (-14, "2. 8-14 days early"),
                                        (-8, "2. 8-14 days early"), (-7, "3. 1-7 days early"),
                                        (0, "4. On estimated day"), (1, "5. 1-3 days late"),
                                        (3, "5. 1-3 days late"), (4, "6. 4-7 days late"),
                                        (8, "7. 8+ days late"), (60, "7. 8+ days late")])
def test_lateness_bucket_boundaries_match_sql(days, label):
    assert kpis.lateness_bucket(pd.Series([days])).iloc[0] == label


def test_lateness_bucket_null_stays_null():
    assert pd.isna(kpis.lateness_bucket(pd.Series([np.nan])).iloc[0])


def test_repeat_rate(order_summary):
    assert kpis.repeat_rate(order_summary) == pytest.approx(0.5)   # u1 has 2 orders, u4 has 1


def test_pareto_share():
    assert kpis.pareto_share(pd.Series([50, 30, 10, 5, 5, 0, 0, 0, 0, 0]), 0.1) == pytest.approx(0.5)
    assert kpis.pareto_share(pd.Series([1, 1, 1, 1]), 0.5) == pytest.approx(0.5)


def test_monthly_trend_mom_and_cumulative(order_summary):
    m = kpis.monthly_trend(order_summary)
    assert m["cumulative_revenue"].iloc[-1] == pytest.approx(m["product_revenue"].sum())
    assert np.isnan(m["revenue_mom_pct"].iloc[0])
