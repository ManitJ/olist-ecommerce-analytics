"""Build the DuckDB database from sql/*.sql and export every named query result.

Named queries in analysis.sql / validation.sql use this header convention:

    -- @query q01_monthly_revenue
    -- @question Is revenue growing month over month?
    SELECT ...;

Usage:
    python -m olist_ba.run_sql            # build db + run validation + analysis
    python -m olist_ba.run_sql --no-build # reuse existing db
"""
from __future__ import annotations

import argparse
import os
import re
from dataclasses import dataclass
from pathlib import Path

import duckdb
import pandas as pd

from .config import DUCKDB_PATH, OUTPUTS, ROOT, SQL_DIR

_HEADER = re.compile(r"^--\s*@query\s+(\w+)\s*$", re.M)


@dataclass
class NamedQuery:
    name: str
    question: str
    sql: str


def connect(path: Path = DUCKDB_PATH, read_only: bool = False) -> duckdb.DuckDBPyConnection:
    path.parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(path), read_only=read_only)


def run_script(con: duckdb.DuckDBPyConnection, path: Path) -> None:
    """Execute a multi-statement SQL file with the repo root as working directory."""
    cwd = os.getcwd()
    os.chdir(ROOT)
    try:
        con.execute(path.read_text())
    finally:
        os.chdir(cwd)


def parse_named_queries(path: Path) -> list[NamedQuery]:
    text = path.read_text()
    starts = [m.start() for m in _HEADER.finditer(text)] + [len(text)]
    out: list[NamedQuery] = []
    for a, b in zip(starts, starts[1:]):
        block = text[a:b]
        name = _HEADER.search(block).group(1)
        q = re.search(r"^--\s*@question\s+(.+)$", block, re.M)
        body = "\n".join(l for l in block.splitlines() if not l.lstrip().startswith("--")).strip()
        # Drop trailing section banners or blank statements after the final semicolon.
        body = body.rstrip().rstrip(";").strip()
        out.append(NamedQuery(name, q.group(1).strip() if q else "", body))
    return out


def run_named(con: duckdb.DuckDBPyConnection, path: Path, out_dir: Path | None = None) -> dict[str, pd.DataFrame]:
    results: dict[str, pd.DataFrame] = {}
    for nq in parse_named_queries(path):
        df = con.execute(nq.sql).df()
        results[nq.name] = df
        if out_dir is not None:
            out_dir.mkdir(parents=True, exist_ok=True)
            df.to_csv(out_dir / f"{nq.name}.csv", index=False)
    return results


def build(con: duckdb.DuckDBPyConnection) -> None:
    run_script(con, SQL_DIR / "schema.sql")
    run_script(con, SQL_DIR / "load.sql")


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--no-build", action="store_true")
    a = p.parse_args(argv)
    con = connect()
    if not a.no_build:
        build(con)
        print(f"Built {DUCKDB_PATH.relative_to(ROOT)}")
    checks = run_named(con, SQL_DIR / "validation.sql", OUTPUTS / "sql" / "validation")
    failed = {k: v for k, v in checks.items() if "status" in v.columns and (v["status"] == "FAIL").any()}
    for k, v in checks.items():
        if "status" in v.columns:
            print(f"  [{'FAIL' if k in failed else 'PASS'}] {k}")
    res = run_named(con, SQL_DIR / "analysis.sql", OUTPUTS / "sql" / "analysis")
    print(f"Exported {len(res)} analysis query results to {(OUTPUTS / 'sql' / 'analysis').relative_to(ROOT)}")
    con.close()
    if failed:
        raise SystemExit(f"Validation failed: {sorted(failed)}")


if __name__ == "__main__":
    main()
