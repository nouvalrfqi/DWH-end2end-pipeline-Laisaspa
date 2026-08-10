"""Central application settings loaded from environment variables (.env).

Single source of truth for connection details, AWS S3 settings, and the
list of source tables. Keeps credentials out of the codebase.
"""

import os

from dotenv import load_dotenv

load_dotenv()

# --- PostgreSQL (Supabase session pooler) ---
PG_HOST = os.getenv("SUPABASE_HOST", "")
PG_PORT = int(os.getenv("SUPABASE_PORT", "5432"))
PG_DATABASE = os.getenv("SUPABASE_DATABASE", "postgres")
PG_USERNAME = os.getenv("SUPABASE_USERNAME", "")
PG_PASSWORD = os.getenv("SUPABASE_PASSWORD", "")
PG_SSLMODE = os.getenv("SUPABASE_SSLMODE", "require")

# --- AWS S3 ---
S3_REGION = os.getenv("AWS_REGION", "ap-southeast-1")
S3_BUCKET = os.getenv("AWS_BUCKET_NAME", "")

# --- Snowflake (analytical warehouse) ---
SF_ACCOUNT = os.getenv("SNOWFLAKE_ACCOUNT", "")
SF_USERNAME = os.getenv("SNOWFLAKE_USERNAME", "")
SF_PASSWORD = os.getenv("SNOWFLAKE_PASSWORD", "")
SF_ROLE = os.getenv("SNOWFLAKE_ROLE", "")
SF_WAREHOUSE = os.getenv("SNOWFLAKE_WAREHOUSE", "")
SF_DATABASE = os.getenv("SNOWFLAKE_DATABASE", "")
SF_SCHEMA = os.getenv("SNOWFLAKE_SCHEMA", "")

# --- Raw data lake layout ---
RAW_PREFIX = "raw"

# --- Source tables (Phase 2 full load; Sprint 2 will move this to YAML) ---
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


def pg_conn_params() -> dict:
    """Return keyword arguments for psycopg2.connect()."""
    return {
        "host": PG_HOST,
        "port": PG_PORT,
        "dbname": PG_DATABASE,
        "user": PG_USERNAME,
        "password": PG_PASSWORD,
        "sslmode": PG_SSLMODE,
        "connect_timeout": 10,
    }


def validate() -> None:
    """Fail fast when required settings are missing.

    AWS credentials are read by boto3 from the environment (load_dotenv
    puts them there), so we only verify presence, not the values.

    NOTE: Snowflake settings are intentionally NOT validated here — they are
    checked by validate_snowflake(), which is called only by the loader.
    The extract pipeline (main.py, tests) must keep working without them.
    """
    required = {
        "SUPABASE_HOST": PG_HOST,
        "SUPABASE_USERNAME": PG_USERNAME,
        "SUPABASE_PASSWORD": PG_PASSWORD,
        "AWS_ACCESS_KEY_ID": os.getenv("AWS_ACCESS_KEY_ID", ""),
        "AWS_SECRET_ACCESS_KEY": os.getenv("AWS_SECRET_ACCESS_KEY", ""),
        "AWS_BUCKET_NAME": S3_BUCKET,
    }
    missing = [name for name, value in required.items() if not value]
    if missing:
        raise RuntimeError(
            f"Missing required environment variables: {missing}. Check .env"
        )


def snowflake_conn_params() -> dict:
    """Return keyword arguments for snowflake.connector.connect()."""
    return {
        "account": SF_ACCOUNT,
        "user": SF_USERNAME,
        "password": SF_PASSWORD,
        "role": SF_ROLE,
        "warehouse": SF_WAREHOUSE,
        "database": SF_DATABASE,
        "schema": SF_SCHEMA,
    }


def validate_snowflake() -> None:
    """Fail fast when Snowflake settings are missing (loader only)."""
    required = {
        "SNOWFLAKE_ACCOUNT": SF_ACCOUNT,
        "SNOWFLAKE_USERNAME": SF_USERNAME,
        "SNOWFLAKE_PASSWORD": SF_PASSWORD,
        "SNOWFLAKE_ROLE": SF_ROLE,
        "SNOWFLAKE_WAREHOUSE": SF_WAREHOUSE,
        "SNOWFLAKE_DATABASE": SF_DATABASE,
        "SNOWFLAKE_SCHEMA": SF_SCHEMA,
    }
    missing = [name for name, value in required.items() if not value]
    if missing:
        raise RuntimeError(
            f"Missing required environment variables: {missing}. Check .env"
        )