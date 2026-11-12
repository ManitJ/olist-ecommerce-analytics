"""Generate dashboard/powerbi/power_query.m from the exported BI tables.

Generating the M code from the real CSV schemas guarantees column names and types in
Power Query always match data/bi/*.csv.

Usage: python -m olist_ba.powerbi_assets   (run after python -m olist_ba.export_bi)
"""
from __future__ import annotations

import pandas as pd

from .config import DATA_BI, ROOT

DATE_COLS = {"date", "month_start", "purchase_date", "purchase_month", "delivered_date", "estimated_delivery_date"}
TEXT_OVERRIDES = {"zip_prefix"}  # keep leading zeros


def m_type(col: str, dtype) -> str:
    if col in DATE_COLS:
        return "type date"
    if col in TEXT_OVERRIDES:
        return "type text"
    if pd.api.types.is_bool_dtype(dtype):
        return "type logical"
    if pd.api.types.is_integer_dtype(dtype):
        return "Int64.Type"
    if pd.api.types.is_float_dtype(dtype):
        return "type number"
    return "type text"


def query_for(table: str) -> str:
    df = pd.read_csv(DATA_BI / f"{table}.csv", nrows=5000, dtype={"zip_prefix": str})
    types = ",\n            ".join(f'{{"{c}", {m_type(c, df[c].dtype)}}}' for c in df.columns)
    return f"""// ---- {table} ----
// Create as: Home > New Source > Blank Query > Advanced Editor, name the query "{table}".
let
    Source = Csv.Document(
        File.Contents(DataFolder & "{table}.csv"),
        [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed = Table.TransformColumnTypes(Promoted, {{
            {types}
        }}, "en-US")
in
    Typed
"""


def main() -> None:
    tables = ["fact_orders", "fact_order_items", "dim_date", "dim_geography", "dim_seller",
              "dim_product", "dim_route", "scenario_results"]
    header = """// =============================================================================
// Power Query (M) for the Olist Delivery Performance model  --  GENERATED FILE
// Generator: python -m olist_ba.powerbi_assets (from data/bi/*.csv headers and dtypes)
//
// 1. Create a text parameter named DataFolder (Home > Manage Parameters > New), value =
//    the absolute path of data/bi/ WITH a trailing separator, e.g. C:\\olist\\data\\bi\\
// 2. Create one blank query per section below and paste its let ... in block.
// Empty CSV fields load as null. Locale "en-US" ensures '.' is read as the decimal mark.
// =============================================================================

// ---- DataFolder (parameter) ----
// "C:\\olist\\data\\bi\\" meta [IsParameterQuery = true, Type = "Text", IsParameterQueryRequired = true]

"""
    out = ROOT / "dashboard" / "powerbi" / "power_query.m"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(header + "\n".join(query_for(t) for t in tables))
    print(f"Wrote {out.relative_to(ROOT)} ({len(tables)} queries)")


if __name__ == "__main__":
    main()
