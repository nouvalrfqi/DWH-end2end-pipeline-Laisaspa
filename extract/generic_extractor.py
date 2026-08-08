"""Configuration-driven generic extractor (Phase 3, Sprint 2).

One framework extracts every configured table to S3 as CSV. No
table-specific extraction code. Batch metadata is written to logs/.
"""

import argparse
import io
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
import yaml
from psycopg2 import sql
from psycopg2.extensions import connection

from config import settings
from extract import postgres_connector, s3_client
from utils import logger

SOURCE_SYSTEM = "supabase_postgresql"
LOAD_TYPE = "full"
CONFIG_PATH = Path("config/tables.yaml")


def load_config() -> dict:
    """Load config/tables.yaml into a dict."""
    with open(CONFIG_PATH, "r") as f:
        return yaml.safe_load(f)


def build_s3_key(table: str, batch_id: str, now: datetime) -> str:
    """raw/<table>/year=YYYY/month=MM/day=DD/<table>_<batch>.csv (ingestion time)."""
    return (
        f"{settings.RAW_PREFIX}/{table}/"
        f"year={now:%Y}/month={now:%m}/day={now:%d}/"
        f"{table}_{batch_id}.csv"
    )


def extract_table(conn: connection, table: str, batch_id: str, now: datetime, log) -> Dict:
    """Extract one table (full load) and upload to S3.

    Always returns a metadata record, even on failure.
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
        query = sql.SQL("SELECT * FROM {table}").format(table=sql.Identifier(table))
        with conn.cursor() as cur:
            cur.execute(query)
            columns = [desc[0] for desc in cur.description]
            rows = cur.fetchall()

        df = pd.DataFrame(rows, columns=columns)
        buffer = io.StringIO()
        df.to_csv(buffer, index=False)

        key = build_s3_key(table, batch_id, now)
        s3_client.upload_bytes(key, buffer.getvalue())

        end = datetime.now()
        record.update({
            "rows_extracted": len(rows),
            "rows_loaded": len(rows),
            "file_path": key,
            "destination": f"s3://{settings.S3_BUCKET}/{key}",
            "end_time": end.isoformat(),
            "duration_seconds": round((end - start).total_seconds(), 3),
            "status": "SUCCESS",
        })
        log.info("OK   %-20s %6d rows -> %s", table, len(rows), key)
    except Exception as exc:
        record.update({
            "end_time": datetime.now().isoformat(),
            "status": "FAILED",
            "error_message": str(exc),
        })
        log.error("FAIL %-20s %s", table, exc)

    return record


def run(tables: Optional[List[str]] = None, batch_id: Optional[str] = None) -> List[Dict]:
    """Run extraction for the given tables (default: all in tables.yaml)."""
    log = logger.setup_logger()
    now = datetime.now()
    batch_id = batch_id or now.strftime("%Y%m%d_%H%M%S")

    config = load_config()
    selected = tables or config["tables"]
    error_policy = config.get("error_policy", "continue")

    conn = postgres_connector.connect()
    records: List[Dict] = []
    try:
        for table in selected:
            record = extract_table(conn, table, batch_id, now, log)
            records.append(record)
            if record["status"] != "SUCCESS" and error_policy == "stop":
                log.error("error_policy=stop -> aborting remaining tables")
                break
    finally:
        conn.close()

    log_path = logger.write_batch_metadata(batch_id, records)
    log.info("Batch %s summary written to %s", batch_id, log_path)
    return records


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generic PostgreSQL -> S3 extractor")
    parser.add_argument("--tables", help="Comma-separated tables (default: all in tables.yaml)")
    parser.add_argument("--batch-id", help="Custom batch id (default: YYYYMMDD_HHMMSS)")
    args = parser.parse_args()

    selected = [t.strip() for t in args.tables.split(",")] if args.tables else None
    summary = run(tables=selected, batch_id=args.batch_id)

    failed = [r for r in summary if r["status"] != "SUCCESS"]
    print(f"\nExtraction: {len(summary) - len(failed)} OK, {len(failed)} FAILED")
    sys.exit(1 if failed else 0)