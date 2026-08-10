"""Test untuk snowflake/ddl_generator.py (Task 3).

Fungsi murni (map_postgres_type, generate_create_table) diuji offline;
fungsi yang butuh koneksi Supabase diuji lewat fake inspect_table.
"""

import pytest

from config import settings
from snowflake import ddl_generator


@pytest.mark.parametrize(
    "pg_type, expected",
    [
        ("uuid", "VARCHAR(36)"),
        ("character varying", "VARCHAR"),
        ("text", "VARCHAR"),
        ("numeric", "NUMBER(38,9)"),
        ("integer", "NUMBER(38,0)"),
        ("bigint", "NUMBER(38,0)"),
        ("smallint", "NUMBER(38,0)"),
        ("double precision", "FLOAT"),
        ("real", "FLOAT"),
        ("boolean", "BOOLEAN"),
        ("timestamp without time zone", "TIMESTAMP_NTZ"),
        ("timestamp with time zone", "TIMESTAMP_TZ"),
        ("date", "DATE"),
        ("jsonb", "VARIANT"),
        ("json", "VARIANT"),
        ("array", "VARIANT"),
    ],
)
def test_map_postgres_type(pg_type, expected):
    assert ddl_generator.map_postgres_type(pg_type) == expected


def test_map_postgres_type_case_insensitive():
    assert ddl_generator.map_postgres_type("JSONB") == "VARIANT"
    assert ddl_generator.map_postgres_type("  Text  ") == "VARCHAR"


def test_map_postgres_type_tipe_tidak_dikenal_memunculkan_error():
    with pytest.raises(RuntimeError, match="Unmapped PostgreSQL type"):
        ddl_generator.map_postgres_type("geometry")


def test_generate_create_table_menghasilkan_ddl_benar():
    columns = [
        ("id", "uuid"),
        ("amount", "numeric"),
        ("created_at", "timestamp without time zone"),
    ]
    ddl = ddl_generator.generate_create_table("transactions", columns)

    assert ddl.startswith(
        "CREATE OR REPLACE TABLE SPA_ANALYTICS.STAGING.transactions ("
    )
    assert "    id VARCHAR(36)" in ddl
    assert "    amount NUMBER(38,9)" in ddl
    assert "    created_at TIMESTAMP_NTZ" in ddl
    assert ddl.endswith("\n);")


def test_generate_create_table_tanpa_kolom_memunculkan_error():
    with pytest.raises(RuntimeError, match="no columns found"):
        ddl_generator.generate_create_table("transactions", [])


def test_generate_ddl_menggunakan_inspect_table_untuk_semua_tabel(monkeypatch):
    """Kunci desain: satu loop untuk semua tabel (bukan per-tabel manual)."""
    from extract import postgres_connector

    calls = []

    def fake_inspect(conn, table):
        calls.append(table)
        return [("id", "uuid")]

    monkeypatch.setattr(postgres_connector, "inspect_table", fake_inspect)

    ddl = ddl_generator.generate_ddl(conn=None, tables=["a", "b"])

    assert calls == ["a", "b"]
    assert "STAGING.a" in ddl
    assert "STAGING.b" in ddl


def test_sumber_tabel_11():
    assert len(settings.SOURCE_TABLES) == 11
