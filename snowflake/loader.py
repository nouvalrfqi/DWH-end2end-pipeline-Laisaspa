"""Snowflake loader: thin SQL runner for staging (Phase 5, Task 4).

--setup  executes the DDL in snowflake/sql/ (01 -> 02 -> 03) using a
         bootstrap connection (only account/user/password/role; the
         database/warehouse are created by the DDL itself).
--load   full load per table: TRUNCATE -> COPY INTO (from the S3 stage) ->
         SELECT COUNT(*) verification, recording per-table metadata.

Only the connection helpers touch snowflake.connector (lazy import), so the
pure SQL builders and load_table are fully testable offline.
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import yaml

from config import settings
from utils import logger

SOURCE_SYSTEM = "aws_s3"
LOAD_TYPE = "full"
STAGING_SCHEMA = "SPA_ANALYTICS.STAGING"
STAGE = "spa_stage"
CSV_PATTERN = r".*\.csv"
SQL_DIR = Path(__file__).resolve().parent / "sql"
CONFIG_PATH = Path("config/tables.yaml")
DDL_FILES = [
    "01_database_warehouse.sql",
    "02_storage_integration.sql",
    "03_staging_tables.sql",
]


def load_config() -> dict:
    """Load config/tables.yaml into a dict."""
    with open(CONFIG_PATH, "r") as f:
        return yaml.safe_load(f)


def connect_snowflake(require_objects: bool = False):
    """Open a Snowflake connection, filtering empty settings.

    Bootstrap mode (--setup) only needs account/user/password/role; the
    database/warehouse/schema are created by the DDL itself, so the empty
    values are dropped from the connect parameters.
    """
    if require_objects:
        settings.validate_snowflake()

    import snowflake.connector  # lazy: only needed for a real connection

    params = {k: v for k, v in settings.snowflake_conn_params().items() if v}
    return snowflake.connector.connect(**params)


def build_truncate_statement(table: str) -> str:
    """Idempotency (PRD section 17): wipe the staging table before COPY."""
    return f"TRUNCATE TABLE {STAGING_SCHEMA}.{table}"


def build_copy_statement(table: str, stage: str = STAGE,
                         pattern: str = CSV_PATTERN) -> str:
    """COPY statement. Stage URL already points at raw/ (Option A), so the
    path is @stage/<table>/ — no extra 'raw/' segment."""
    return (
        f"COPY INTO {STAGING_SCHEMA}.{table} "
        f"FROM @{stage}/{table}/ PATTERN='{pattern}' "
        "ON_ERROR='ABORT_STATEMENT'"
    )


def load_table(conn, table: str, batch_id: str, log,
               stage: str = STAGE) -> Dict:
    """Load one table: TRUNCATE -> COPY INTO -> COUNT. Returns metadata.

    Always returns a record, even on failure (continue policy is handled
    by the caller).
    """
    start = datetime.now()
    record = {
        "source_system": SOURCE_SYSTEM,
        "source_table": table,
        "batch_id": batch_id,
        "start_time": start.isoformat(),
        "load_type": LOAD_TYPE,
        "status": "PENDING",
    }

    try:
        with conn.cursor() as cur:
            cur.execute(build_truncate_statement(table))
            cur.execute(build_copy_statement(table, stage))
            cur.execute(f"SELECT COUNT(*) FROM {STAGING_SCHEMA}.{table}")
            rows_loaded = cur.fetchone()[0]

        end = datetime.now()
        record.update({
            "rows_loaded": rows_loaded,
            "destination": f"{STAGING_SCHEMA}.{table}",
            "end_time": end.isoformat(),
            "duration_seconds": round((end - start).total_seconds(), 3),
            "status": "SUCCESS",
        })
        log.info("OK   %-20s %d rows loaded", table, rows_loaded)
    except Exception as exc:
        record.update({
            "end_time": datetime.now().isoformat(),
            "status": "FAILED",
            "error_message": str(exc),
        })
        log.error("FAIL %-20s %s", table, exc)

    return record


def run_load(tables: Optional[List[str]] = None,
             batch_id: Optional[str] = None) -> List[Dict]:
    """Full load for the given tables (default: all in tables.yaml)."""
    settings.validate_snowflake()
    log = logger.setup_logger("load")
    now = datetime.now()
    batch_id = batch_id or now.strftime("%Y%m%d_%H%M%S")

    config = load_config()
    selected = tables or config["tables"]
    error_policy = config.get("error_policy", "continue")

    conn = connect_snowflake(require_objects=True)
    records: List[Dict] = []
    try:
        for table in selected:
            record = load_table(conn, table, batch_id, log)
            records.append(record)
            if record["status"] != "SUCCESS" and error_policy == "stop":
                log.error("error_policy=stop -> aborting remaining tables")
                break
    finally:
        conn.close()

    log_path = logger.write_batch_metadata(batch_id, records, prefix="load")
    log.info("Batch %s load summary written to %s", batch_id, log_path)
    return records


def execute_sql_script(conn, sql_text: str) -> int:
    """Run every statement in a SQL script, splitting on ';'."""
    executed = 0
    with conn.cursor() as cur:
        for chunk in sql_text.split(";"):
            statement = chunk.strip()
            if not statement:
                continue
            cur.execute(statement)
            executed += 1
    return executed


def verify_setup(conn) -> int:
    """Report how many staging tables exist after setup."""
    with conn.cursor() as cur:
        cur.execute(f"SHOW TABLES IN {STAGING_SCHEMA}")
        tables = cur.fetchall()
    print(f"[setup] STAGING tables found: {len(tables)}")
    return len(tables)


def run_setup() -> None:
    """Execute DDL 01 -> 02 -> 03 with a bootstrap connection."""
    conn = connect_snowflake(require_objects=False)
    try:
        for filename in DDL_FILES:
            script = (SQL_DIR / filename).read_text()
            count = execute_sql_script(conn, script)
            print(f"[setup] {filename}: {count} statement(s) executed")
        verify_setup(conn)
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Snowflake staging loader")
    parser.add_argument("--setup", action="store_true",
                        help="Run DDL 01-03 (database/warehouse, integration, tables)")
    parser.add_argument("--tables",
                        help="Comma-separated tables (default: all in tables.yaml)")
    parser.add_argument("--batch-id",
                        help="Custom batch id (default: YYYYMMDD_HHMMSS)")
    args = parser.parse_args()

    if args.setup:
        run_setup()
        return

    selected = [t.strip() for t in args.tables.split(",")] if args.tables else None
    summary = run_load(tables=selected, batch_id=args.batch_id)

    failed = [r for r in summary if r["status"] != "SUCCESS"]
    print(f"\nLoad: {len(summary) - len(failed)} OK, {len(failed)} FAILED")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
