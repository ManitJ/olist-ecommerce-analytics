"""Scenario model logic and its Power BI (DAX) replication."""
import numpy as np
import pandas as pd
import pytest

from conftest import integration
from olist_ba.config import DATA_BI, OUTPUTS
from olist_ba.scenarios import ASSUMPTIONS, attributable_shares


def _toy():
    """60 orders. Lane A->B: 30 orders, 12 late. Lane A->A: 30 orders, 0 late.
    6 seller SLA misses, all late. No peak months."""
    one = pd.DataFrame({
        "route": ["A->B"] * 10 + ["A->A"] * 10,
        "is_late": [1, 1, 1, 1] + [0] * 16,
        "seller_shipped_late": [1, 1] + [0] * 18,
        "purchase_month": [pd.Timestamp("2017-10-01")] * 20,
    })
    d = pd.concat([one] * 3, ignore_index=True)
    d["order_id"] = [f"o{i}" for i in range(len(d))]
    return d


def test_attributable_shares_use_only_excess():
    d = _toy()
    s, meta = attributable_shares(d, n_lanes=1)
    base = 12 / 60                       # platform late rate 20%
    lane = 12 / 30                       # A->B late rate 40%
    on_lane = d["route"] == "A->B"
    assert s.loc[on_lane, "L1"].unique().tolist() == [pytest.approx((lane - base) / lane)]   # 0.5
    assert (s.loc[~on_lane, "L1"] == 0).all()                  # A->A is not a target lane
    miss_rate, ok_rate = 6 / 6, 6 / 54
    assert meta["L2_attributable_share"] == pytest.approx(round((miss_rate - ok_rate) / miss_rate, 4))
    assert (s.loc[d["seller_shipped_late"] == 0, "L2"] == 0).all()
    assert (s["L4"] == 0).all()                                # no peak months in the toy data


def test_zero_assumptions_avoid_nothing():
    d = _toy()
    s, _ = attributable_shares(d, n_lanes=1)
    late = d["is_late"] == 1
    p = 1 - (1 - s["L1"] * 0) * (1 - s["L2"] * 0) * (1 - s["L4"] * 0)
    assert p[late].sum() == 0


@integration
def test_dax_formula_replicates_python_scenarios():
    """The DAX 'Scenario Late Orders Avoided' formula, evaluated in pandas on the exported fact table,
    must equal the python scenario output for every case."""
    f = pd.read_csv(DATA_BI / "fact_orders.csv")
    res = pd.read_csv(OUTPUTS / "scenarios" / "scenario_results.csv")
    b = f[f["is_scenario_baseline"] == 1]
    late = b["is_late"] == 1
    for case in ("low", "base", "high"):
        r1 = ASSUMPTIONS["L1_lane_recovery_excess_reduction"][case]
        r2 = ASSUMPTIONS["L2_seller_sla_conversion"][case]
        r4 = ASSUMPTIONS["L4_peak_excess_reduction"][case]
        p = 1 - (1 - b["lever_l1_share"] * r1) * (1 - b["lever_l2_share"] * r2) * (1 - b["lever_l4_share"] * r4)
        expected = res[(res["case"] == case) & res["lever"].str.startswith("Combined")]["late_orders_avoided"].iloc[0]
        assert round(p[late].sum()) == expected, case


@integration
def test_combined_effect_is_less_than_sum_of_levers():
    res = pd.read_csv(OUTPUTS / "scenarios" / "scenario_results.csv")
    for case, g in res.groupby("case"):
        singles = g[g["lever"].isin(["L1", "L2", "L4"])]["late_orders_avoided"].sum()
        combined = g[g["lever"].str.startswith("Combined")]["late_orders_avoided"].iloc[0]
        assert combined <= singles, case


@integration
def test_sensitivity_monotonic_and_zero_at_zero():
    s = pd.read_csv(OUTPUTS / "scenarios" / "sensitivity.csv")
    assert s.loc[0, "late_orders_avoided"] == 0
    assert np.all(np.diff(s["late_orders_avoided"]) > 0)
