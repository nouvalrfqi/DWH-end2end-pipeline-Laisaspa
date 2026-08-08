"""Sprint 1 acceptance: verify PostgreSQL + S3 connectivity end to end."""

import sys

from config import settings
from extract import postgres_connector, s3_client


def check_postgres() -> bool:
    try:
        settings.validate()
    except RuntimeError as exc:
        print(f"FAIL postgres: {exc}")
        return False

    try:
        conn = postgres_connector.connect()
        with conn.cursor() as cur:
            cur.execute("SELECT version();")
            version = cur.fetchone()[0].split(" on ")[0]
        print(f"PASS postgres: connected ({version})")

        for table in settings.SOURCE_TABLES:
            count = postgres_connector.fetch_row_count(conn, table)
            columns = postgres_connector.inspect_table(conn, table)
            print(f"  {table:20s} {count:>8,} rows  ({len(columns)} columns)")
        conn.close()
        return True
    except Exception as exc:
        print(f"FAIL postgres: {exc}")
        return False


def check_s3() -> bool:
    try:
        client = s3_client.get_client()
    except Exception as exc:
        print(f"FAIL s3: {exc}")
        return False

    if not s3_client.bucket_exists(client):
        print(f"FAIL s3: bucket '{settings.S3_BUCKET}' not reachable")
        return False
    print(f"PASS s3: authenticated, bucket '{settings.S3_BUCKET}' reachable")

    try:
        key = s3_client.upload_test_object(client)
        print(f"PASS s3: test object verified + deleted  s3://{settings.S3_BUCKET}/{key}")
        return True
    except Exception as exc:
        print(f"FAIL s3: test upload failed: {exc}")
        return False


if __name__ == "__main__":
    postgres_ok = check_postgres()
    s3_ok = check_s3()
    print()
    if postgres_ok and s3_ok:
        print("Sprint 1 acceptance: ALL PASS")
        sys.exit(0)
    print("Sprint 1 acceptance: FAIL")
    sys.exit(1)