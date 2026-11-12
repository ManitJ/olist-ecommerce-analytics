"""SQL deliverable checks: query count/features, determinism, and T-SQL syntax."""
import re

import sqlglot

from conftest import integration
from olist_ba.config import SQL_DIR
from olist_ba.run_sql import connect, parse_named_queries


def test_at_least_15_named_analysis_queries_with_questions():
    qs = parse_named_queries(SQL_DIR / "analysis.sql")
    assert len(qs) >= 15
    assert all(q.question for q in qs), "every query must state the business question it answers"


def test_analysis_sql_uses_required_techniques():
    s = (SQL_DIR / "analysis.sql").read_text().upper()
    for kw in ["JOIN", "WITH ", "CASE WHEN", "GROUP BY", "OVER (", "LAG(", "RANK()", "NTILE(", "ROW_NUMBER()",
               "DATE_DIFF", "ROWS BETWEEN"]:
        assert kw in s, kw


def test_no_positional_group_or_order_by():
    s = (SQL_DIR / "analysis.sql").read_text()
    assert not re.search(r"(GROUP|ORDER) BY \d", s), "positional references do not port to T-SQL"


def test_tsql_files_parse():
    for f in ("analysis.sql", "validation.sql"):
        text = (SQL_DIR / "tsql" / f).read_text()
        batches = [b for b in re.split(r"^\s*GO\s*$", text, flags=re.M) if b.strip()]
        assert len(batches) >= 8
        for b in batches:
            sqlglot.parse(b, read="tsql")


@integration
def test_window_function_queries_are_deterministic():
    """NTILE / ROW_NUMBER with ties must use explicit tie-breakers (regression test)."""
    con = connect(read_only=True)
    qs = {q.name: q.sql for q in parse_named_queries(SQL_DIR / "analysis.sql")}
    for name in ("q10_seller_concentration", "q14_first_delivery_vs_repeat", "q15_rfm_segments"):
        a = con.execute(qs[name]).df()
        b = con.execute(qs[name]).df()
        assert a.equals(b), name
    con.close()
