"""Generate SQL Server (T-SQL) versions of analysis.sql and validation.sql.

DuckDB is the tested engine. This script transpiles each named query with sqlglot,
applies a small set of documented post-processing rules, substitutes hand-written
T-SQL for queries that use constructs with no direct T-SQL equivalent (aggregate
MEDIAN), and then parse-checks every output statement with sqlglot's T-SQL parser.

A parse check proves the output is syntactically valid T-SQL; it does NOT prove the
queries return the same results on SQL Server. See sql/tsql/README.md.

Usage: python -m olist_ba.transpile_tsql
"""
from __future__ import annotations

import re

import sqlglot
from sqlglot.errors import ErrorLevel

from .config import SQL_DIR
from .run_sql import parse_named_queries

# Hand-written T-SQL for queries that use aggregate MEDIAN (not available in T-SQL).
# Pattern: PERCENTILE_CONT as a window function per group, then collapse with MAX().
OVERRIDES = {
    "q08_fulfilment_stage_trend": """
WITH base AS (
    SELECT purchase_month, approval_hours, seller_to_carrier_days, carrier_to_customer_days,
           delivery_days, promised_days, is_late
    FROM dw.v_order_summary
    WHERE in_window = 1 AND is_delivered = 1
      AND dq_carrier_before_approval = 0 AND dq_delivered_before_carrier = 0
), med AS (
    SELECT *,
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY approval_hours)           OVER (PARTITION BY purchase_month) AS m_appr,
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY seller_to_carrier_days)   OVER (PARTITION BY purchase_month) AS m_s2c,
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY carrier_to_customer_days) OVER (PARTITION BY purchase_month) AS m_c2c,
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY delivery_days)            OVER (PARTITION BY purchase_month) AS m_dd
    FROM base
)
SELECT purchase_month,
       COUNT(*)                          AS delivered_orders,
       ROUND(MAX(m_appr), 1)             AS median_approval_hours,
       ROUND(MAX(m_s2c), 2)              AS median_seller_to_carrier_days,
       ROUND(MAX(m_c2c), 2)              AS median_carrier_to_customer_days,
       ROUND(MAX(m_dd), 2)               AS median_delivery_days,
       ROUND(AVG(promised_days * 1.0), 1) AS avg_promised_days,
       ROUND(AVG(is_late * 1.0), 4)      AS late_rate
FROM med
GROUP BY purchase_month
ORDER BY purchase_month""",
    "q17_installments_vs_aov": """
WITH b AS (
    SELECT product_revenue,
           CASE WHEN max_installments <= 1 THEN '1 (single payment)'
                WHEN max_installments <= 3 THEN '2-3'
                WHEN max_installments <= 6 THEN '4-6'
                ELSE '7+' END AS installment_band
    FROM dw.v_order_summary
    WHERE in_window = 1 AND is_revenue_order = 1 AND max_installments IS NOT NULL
), m AS (
    SELECT *, PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY product_revenue)
                  OVER (PARTITION BY installment_band) AS med
    FROM b
)
SELECT installment_band,
       COUNT(*)                         AS orders,
       ROUND(AVG(product_revenue), 2)   AS aov,
       ROUND(MAX(med), 2)               AS median_order_value,
       ROUND(100.0 * SUM(product_revenue) / SUM(SUM(product_revenue)) OVER (), 2) AS revenue_share_pct
FROM m
GROUP BY installment_band
ORDER BY installment_band""",
}

# Post-processing for constructs sqlglot emits that are not valid T-SQL.
POST_RULES = [
    # ISO weekday (1 = Monday) independent of the server's @@DATEFIRST setting
    (re.compile(r"DAYOFWEEK_ISO\(([^()]+)\)"), r"((DATEPART(WEEKDAY, \1) + @@DATEFIRST - 2) % 7 + 1)"),
]

BANNER = """/* =============================================================================
   {name} (SQL Server 2022 / T-SQL)  --  GENERATED FILE, do not edit by hand.
   Source: sql/{name} (DuckDB). Generator: python -m olist_ba.transpile_tsql
   (sqlglot {ver}). Every statement below was parse-checked as T-SQL, but has NOT
   been executed against SQL Server. Queries {overrides} are hand-written.
   Run after sql/tsql/schema.sql and sql/tsql/load.sql.
   ============================================================================= */
"""


def transpile_query(name: str, sql: str) -> str:
    if name in OVERRIDES:
        out = OVERRIDES[name].strip()
    else:
        # IGNORE: DuckDB sorts NULLs last by default and T-SQL sorts them first. That only
        # affects row ORDER for keys that are never NULL here, so it is safe to ignore.
        out = sqlglot.transpile(sql, read="duckdb", write="tsql", pretty=True,
                                unsupported_level=ErrorLevel.IGNORE)[0]
        for pat, rep in POST_RULES:
            out = pat.sub(rep, out)
    sqlglot.parse_one(out, read="tsql")  # raises on invalid syntax
    return out


def generate(src_name: str) -> list[str]:
    queries = parse_named_queries(SQL_DIR / src_name)
    used = [q.name for q in queries if q.name in OVERRIDES]
    parts = [BANNER.format(name=src_name, ver=sqlglot.__version__, overrides=", ".join(used) or "(none)")]
    for q in queries:
        parts.append(f"-- @query {q.name}\n-- @question {q.question}\n{transpile_query(q.name, q.sql)};\nGO\n")
    (SQL_DIR / "tsql" / src_name).write_text("\n".join(parts))
    return [q.name for q in queries]


def parse_check_handwritten() -> None:
    """Parse-check the hand-ported schema/load scripts (sqlcmd directives stripped)."""
    for f in ("schema.sql", "load.sql"):
        text = (SQL_DIR / "tsql" / f).read_text()
        text = re.sub(r"^:setvar.*$", "", text, flags=re.M)
        # sqlglot cannot parse BULK INSERT; check its shape with a regex instead.
        bulk = re.compile(r"^BULK INSERT stg\.\w+\s+FROM '\$\(RawDir\)\\[\w.]+\.csv'\s+WITH \(.+\);$", re.M)
        n_bulk = len(re.findall(r"^BULK INSERT", text, flags=re.M))
        assert n_bulk == len(bulk.findall(text)), f"{f}: malformed BULK INSERT statement"
        text = bulk.sub("", text)
        for batch in re.split(r"^\s*GO\s*$", text, flags=re.M):
            if batch.strip():
                sqlglot.parse(batch, read="tsql")


def main() -> None:
    for f in ("analysis.sql", "validation.sql"):
        names = generate(f)
        print(f"sql/tsql/{f}: {len(names)} queries transpiled and parse-checked")
    parse_check_handwritten()
    print("sql/tsql/schema.sql, load.sql: parse-checked")


if __name__ == "__main__":
    main()
