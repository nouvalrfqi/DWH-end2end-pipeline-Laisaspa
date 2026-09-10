"""Tests for warehouse/loader.py.

All tests run offline: the Snowflake connection is replaced with
FakeSnowflakeConnection (see tests/fakes.py), so snowflake.connector is
never touched.
"""

import json
import sys

from config import settings
from fakes import FakeSnowflakeConnection
from warehouse import loader


class _NullLog:
    """Logger replacement that prints nothing during the test."""

    def info(self, *args, **kwargs):
        pass

    def error(self, *args, **kwargs):
        pass


def _set_snowflake_settings(monkeypatch, value="dummy"):
    """Fill every SF_* setting so validate_snowflake() passes."""
    for name in ["SF_ACCOUNT", "SF_USERNAME", "SF_PASSWORD", "SF_ROLE",
                 "SF_WAREHOUSE", "SF_DATABASE", "SF_SCHEMA"]:
        monkeypatch.setattr(settings, name, value)


# ---------- execute_sql_script ----------

def test_execute_sql_script_skips_comments_and_empty_statements():
    conn = FakeSnowflakeConnection()
    sql = (
        "-- comment with a semicolon: SET X = 'y';\n"
        "\n"
        "CREATE DATABASE IF NOT EXISTS SPA_ANALYTICS;\n"
        "CREATE WAREHOUSE IF NOT EXISTS SPA_WH;\n"
    )
    count = loader.execute_sql_script(conn, sql)

    assert count == 2
    # comments must not produce an 'Empty SQL statement' error
    assert conn.executed == [
        "CREATE DATABASE IF NOT EXISTS SPA_ANALYTICS",
        "CREATE WAREHOUSE IF NOT EXISTS SPA_WH",
    ]


# ---------- build_truncate_statement ----------

def test_build_truncate_statement():
    assert loader.build_truncate_statement("transactions") == (
        "TRUNCATE TABLE SPA_ANALYTICS.STAGING.transactions"
    )


# ---------- build_copy_statement ----------

def test_build_copy_statement_option_a():
    """Option A: stage points at raw/, so COPY uses @spa_stage/<table>/."""
    sql = loader.build_copy_statement("transactions")
    assert sql == (
        "COPY INTO SPA_ANALYTICS.STAGING.transactions "
        "FROM @spa_stage/transactions/ PATTERN='.*\\.csv' "
        "ON_ERROR='ABORT_STATEMENT'"
    )


# ---------- load_table: SUCCESS ----------

def test_load_table_success_executes_sql_in_order():
    conn = FakeSnowflakeConnection(count=179)
    record = loader.load_table(conn, "transactions", "batch_1", _NullLog())

    assert record["status"] == "SUCCESS"
    assert record["rows_loaded"] == 179
    assert record["source_table"] == "transactions"
    # operation order: 1) TRUNCATE  2) COPY INTO  3) SELECT COUNT(*)
    assert conn.executed[0].startswith("TRUNCATE TABLE")
    assert conn.executed[1].startswith("COPY INTO")
    assert "SELECT COUNT(*)" in conn.executed[2]


# ---------- load_table: FAILED ----------

def test_load_table_failure_captures_error_and_continues():
    conn = FakeSnowflakeConnection(count=0, fail_on="COPY INTO")
    record = loader.load_table(conn, "transactions", "batch_1", _NullLog())

    assert record["status"] == "FAILED"
    assert "simulated error" in record["error_message"]
    assert "rows_loaded" not in record


# ---------- connect_snowflake: bootstrap filter ----------

def test_connect_snowflake_filters_empty_params(monkeypatch):
    """Bootstrap: empty DB/warehouse/schema must be dropped from params."""
    captured = {}

    class FakeConnectorModule:
        @staticmethod
        def connect(**params):
            captured.update(params)
            return "conn"

    fake_connector = FakeConnectorModule()
    import snowflake  # real pip package (local project package is now warehouse/)

    # inject into sys.modules + parent attribute so `import snowflake.connector`
    # resolves to the fake module
    monkeypatch.setitem(sys.modules, "snowflake.connector", fake_connector)
    monkeypatch.setattr(snowflake, "connector", fake_connector, raising=False)
    _set_snowflake_settings(monkeypatch, value="dummy")
    for name in ["SF_WAREHOUSE", "SF_DATABASE", "SF_SCHEMA"]:
        monkeypatch.setattr(settings, name, "")

    result = loader.connect_snowflake(require_objects=False)

    assert result == "conn"
    assert captured["account"] == "dummy"
    assert "warehouse" not in captured   # empty -> dropped
    assert "database" not in captured
    assert "schema" not in captured


# ---------- run_load: continue policy + metadata ----------

def test_run_load_error_policy_continue_processes_all(monkeypatch, tmp_path):
    """With 'continue', one failed table must not stop the others."""
    monkeypatch.setattr(loader.logger, "LOGS_DIR", tmp_path)
    monkeypatch.setattr(loader.logger, "setup_logger",
                        lambda name="extract": _NullLog())
    monkeypatch.setattr(loader, "connect_snowflake",
                        lambda require_objects=False: FakeSnowflakeConnection(fail_on="COPY INTO"))
    monkeypatch.setattr(loader, "load_config",
                        lambda: {"tables": ["a", "b", "c"], "error_policy": "continue"})
    _set_snowflake_settings(monkeypatch)

    records = loader.run_load(batch_id="test_continue")

    assert len(records) == 3          # every table is still processed
    assert all(r["status"] == "FAILED" for r in records)

    # metadata is written to logs/load_log_<batch>.json
    log_path = tmp_path / "load_log_test_continue.json"
    assert log_path.exists()
    payload = json.loads(log_path.read_text())
    assert payload["batch_id"] == "test_continue"
    assert len(payload["tables"]) == 3