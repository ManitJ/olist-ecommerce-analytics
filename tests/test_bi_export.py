"""Power BI star schema integrity: unique keys on dimensions, full FK coverage from facts."""
import pandas as pd
import pytest

from conftest import integration
from olist_ba.config import DATA_BI

pytestmark = integration


@pytest.fixture(scope="module")
def t():
    names = ["fact_orders", "fact_order_items", "dim_date", "dim_geography", "dim_seller", "dim_product", "dim_route"]
    return {n: pd.read_csv(DATA_BI / f"{n}.csv", dtype={"zip_prefix": str}) for n in names}


@pytest.mark.parametrize("dim,key", [("dim_date", "date"), ("dim_geography", "state"), ("dim_seller", "seller_id"),
                                     ("dim_product", "product_id"), ("dim_route", "route")])
def test_dimension_keys_unique(t, dim, key):
    assert t[dim][key].is_unique


@pytest.mark.parametrize("fact,fk,dim,key", [
    ("fact_orders", "purchase_date", "dim_date", "date"),
    ("fact_orders", "customer_state", "dim_geography", "state"),
    ("fact_orders", "seller_id", "dim_seller", "seller_id"),
    ("fact_orders", "route", "dim_route", "route"),
    ("fact_order_items", "product_id", "dim_product", "product_id"),
    ("fact_order_items", "seller_id", "dim_seller", "seller_id"),
    ("fact_order_items", "purchase_date", "dim_date", "date"),
])
def test_fact_foreign_keys_resolve(t, fact, fk, dim, key):
    vals = t[fact][fk].dropna()
    assert vals.isin(t[dim][key]).all(), f"{fact}.{fk} has values missing from {dim}.{key}"


def test_fact_grain(t):
    assert t["fact_orders"]["order_id"].is_unique and len(t["fact_orders"]) == 99441
    assert len(t["fact_order_items"]) == 112650


def test_regions_cover_all_states(t):
    assert t["dim_geography"]["region"].notna().all() and len(t["dim_geography"]) == 27


def test_power_query_columns_match_csv():
    from olist_ba.config import ROOT
    m = (ROOT / "dashboard" / "powerbi" / "power_query.m").read_text()
    header = pd.read_csv(DATA_BI / "fact_orders.csv", nrows=0).columns
    for c in header:
        assert f'{{"{c}",' in m, c
