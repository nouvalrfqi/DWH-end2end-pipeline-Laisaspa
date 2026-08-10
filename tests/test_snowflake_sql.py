"""Test untuk snowflake/sql/ DDL (Task 2).

Goal: melindungi kontrak DDL secara offline — file ada, non-kosong, dan
tetap idempotent (IF NOT EXISTS) supaya aman dijalankan berulang (PRD §17).
03_staging_tables.sql belum ada di Task 2 — lahir dari ddl_generator (Task 3).
"""

from pathlib import Path

SQL_DIR = Path(__file__).resolve().parents[1] / "snowflake" / "sql"


def _read_sql(filename: str) -> str:
    path = SQL_DIR / filename
    assert path.exists(), f"{filename} tidak ditemukan di snowflake/sql/"
    return path.read_text()


def test_01_database_warehouse_ada_dan_berisi():
    content = _read_sql("01_database_warehouse.sql")
    assert content.strip(), "01 harus berisi DDL"
    assert "CREATE DATABASE IF NOT EXISTS SPA_ANALYTICS" in content
    assert "CREATE WAREHOUSE IF NOT EXISTS SPA_WH" in content
    for schema in ["STAGING", "WAREHOUSE", "MART"]:
        assert f"CREATE SCHEMA IF NOT EXISTS SPA_ANALYTICS.{schema}" in content


def test_02_storage_integration_ada_dan_idempotent():
    content = _read_sql("02_storage_integration.sql")
    assert content.strip(), "02 harus berisi DDL"
    assert "CREATE FILE FORMAT IF NOT EXISTS" in content
    assert "CREATE STORAGE INTEGRATION IF NOT EXISTS" in content
    assert "CREATE STAGE IF NOT EXISTS" in content


def test_02_file_format_csv_memiliki_param_kunci():
    content = _read_sql("02_storage_integration.sql")
    assert "SKIP_HEADER" in content
    assert "FIELD_OPTIONALLY_ENCLOSED_BY" in content
    assert "EMPTY_FIELD_AS_NULL" in content
    assert "NULL_IF" in content
    assert "ERROR_ON_COLUMN_COUNT_MISMATCH" in content


def test_02_stage_url_menunjuk_raw_prefix():
    """Opsi A: stage menunjuk ke raw/ sehingga COPY pakai @spa_stage/<table>/."""
    content = _read_sql("02_storage_integration.sql")
    assert "s3://spa-data-platform-dev/raw/" in content
