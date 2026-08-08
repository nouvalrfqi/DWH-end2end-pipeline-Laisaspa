import os
import sys

import boto3
import psycopg2
from botocore.exceptions import BotoCoreError, ClientError
from dotenv import load_dotenv

SOURCE_TABLES = [
    "treatments",
    "spa_products",
    "booking_groups",
    "booking_logs",
    "transactions",
    "completed_items",
    "members",
    "gift_cards",
    "reviews",
    "spa_consultations",
    "site_settings",
]

load_dotenv()


def check_postgres() -> bool:
    required = ["SUPABASE_HOST", "SUPABASE_PORT", "SUPABASE_DATABASE", "SUPABASE_USERNAME", "SUPABASE_PASSWORD"]
    missing = [k for k in required if not os.environ.get(k)]
    if missing:
        print(f"FAIL postgres: missing env vars {missing}")
        return False

    try:
        conn = psycopg2.connect(
            host=os.environ["SUPABASE_HOST"],
            port=os.environ["SUPABASE_PORT"],
            dbname=os.environ["SUPABASE_DATABASE"],
            user=os.environ["SUPABASE_USERNAME"],
            password=os.environ["SUPABASE_PASSWORD"],
            sslmode="require",
            connect_timeout=10,
        )
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("SELECT version();")
            version = cur.fetchone()[0].split(" on ")[0]
        print(f"PASS postgres: connected ({version})")

        with conn.cursor() as cur:
            for table in SOURCE_TABLES:
                try:
                    cur.execute(f'SELECT COUNT(*) FROM "{table}";')
                    count = cur.fetchone()[0]
                    print(f"  {table:20s} {count:>8,} rows")
                except Exception as exc:
                    print(f"  {table:20s} ERROR: {exc}")
        conn.close()
        return True
    except Exception as exc:
        print(f"FAIL postgres: {exc}")
        return False


def check_s3() -> bool:
    required = ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_REGION", "AWS_BUCKET_NAME"]
    missing = [k for k in required if not os.environ.get(k)]
    if missing:
        print(f"FAIL s3: missing env vars {missing}")
        return False

    try:
        client = boto3.client("s3", region_name=os.environ["AWS_REGION"])
        bucket = os.environ["AWS_BUCKET_NAME"]
        client.head_bucket(Bucket=bucket)
        print(f"PASS s3: authenticated, bucket '{bucket}' reachable")
        return True
    except (ClientError, BotoCoreError) as exc:
        print(f"FAIL s3: {exc}")
        return False


if __name__ == "__main__":
    postgres_ok = check_postgres()
    s3_ok = check_s3()
    print()
    if postgres_ok and s3_ok:
        print("Connectivity: ALL PASS")
        sys.exit(0)
    else:
        print("Connectivity: FAIL")
        sys.exit(1)
