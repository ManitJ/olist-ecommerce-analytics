# SQL Server 2022 (T-SQL) port

## Status, stated precisely
| File | How it was produced | Verified by |
|---|---|---|
| `schema.sql` | Hand-ported from `../schema.sql` | sqlglot T-SQL parser (syntax only) |
| `load.sql` | Hand-ported (`BULK INSERT`, `DATETRUNC`, `TRY_CAST`, `GO` batches) | sqlglot parser, plus a regex check on `BULK INSERT` statements |
| `analysis.sql` | **Generated** by `python -m olist_ba.transpile_tsql` (sqlglot), with hand-written overrides for q08 and q17 (no aggregate `MEDIAN` in T-SQL; replaced with windowed `PERCENTILE_CONT`) | sqlglot parser |
| `validation.sql` | Generated as above | sqlglot parser |

**None of these files has been executed on SQL Server.** Parse-checking proves the syntax is valid T-SQL. It does not prove the results match DuckDB. Before relying on them, check them on a SQL Server instance.

## How to run and verify on SQL Server
1. Create a database, for example `CREATE DATABASE olist;`.
2. Run the schema:
   `sqlcmd -S <server> -d olist -i sql/tsql/schema.sql`
3. Load the data. Run this in SQLCMD mode, and make sure the CSVs are readable by the SQL Server service account:
   `sqlcmd -S <server> -d olist -v RawDir="C:\path\to\data\raw" -i sql/tsql/load.sql`
4. Validate. Every `status` must be PASS or INFO:
   `sqlcmd -S <server> -d olist -i sql/tsql/validation.sql`
5. Run the analysis: `sqlcmd -S <server> -d olist -i sql/tsql/analysis.sql`. Compare the outputs with `outputs/sql/analysis/*.csv` from DuckDB.

On macOS or Linux you can run SQL Server 2022 in Docker (`mcr.microsoft.com/mssql/server:2022-latest`). It needs about 2 GB of RAM and several GB of disk.

## Known dialect differences to watch
- **NULL ordering.** DuckDB sorts NULLs last; T-SQL sorts them first. The generator emulates NULLS LAST with `CASE` in `ORDER BY`.
- **ISO weekday.** It is computed as `(DATEPART(WEEKDAY, x) + @@DATEFIRST - 2) % 7 + 1`, so it does not depend on server settings.
- **Accent stripping.** `load.sql` folds accents with a code-page conversion (`COLLATE SQL_Latin1_General_CP1253_CI_AI`). This is a common technique, but it is the step most likely to differ from DuckDB's `strip_accents`. City names are not used in any KPI.
- **Integer division.** All rates multiply by `1.0` before dividing, so integer division does not truncate them.
