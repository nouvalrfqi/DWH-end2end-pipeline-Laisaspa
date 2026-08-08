"""PostgreSQL connector: connection with retry + schema/row inspection.

Table names are quoted safely with psycopg2.sql.Identifier to prevent
SQL injection (defensive practice even though names come from our config).
"""

import time
from typing import List, Optional, Tuple

import psycopg2
from psycopg2 import sql
from psycopg2.extensions import connection

from config import settings

DEFAULT_MAX_RETRIES = 3
RETRY_BASE_DELAY_SECONDS = 2


def connect(max_retries: int = DEFAULT_MAX_RETRIES) -> connection:
    """Open a connection, retrying transient failures with exponential backoff."""
    last_error: Optional[Exception] = None
    for attempt in range(1, max_retries + 1):
        try:
            return psycopg2.connect(**settings.pg_conn_params())
        except (psycopg2.OperationalError, psycopg2.InterfaceError) as exc:
            last_error = exc
            if attempt < max_retries:
                delay = RETRY_BASE_DELAY_SECONDS * (2 ** (attempt - 1))
                print(f"[postgres] attempt {attempt}/{max_retries} failed; retrying in {delay}s")
                time.sleep(delay)
    raise RuntimeError(
        f"Could not connect to PostgreSQL after {max_retries} attempts: {last_error}"
    )


def fetch_row_count(conn: connection, table: str) -> int:
    """Return the number of rows in `table`."""
    with conn.cursor() as cur:
        cur.execute(
            sql.SQL("SELECT COUNT(*) FROM {table}").format(table=sql.Identifier(table))
        )
        return cur.fetchone()[0]


def inspect_table(conn: connection, table: str) -> List[Tuple[str, str]]:
    """Return [(column_name, data_type), ...] for `table` in the public schema."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = %s
            ORDER BY ordinal_position
            """,
            (table,),
        )
        return cur.fetchall()