"""Test untuk snowflake/loader.py (Task 4).

Semua test offline: koneksi Snowflake diganti FakeSnowflakeConnection
(lihat tests/fakes.py) sehingga snowflake.connector tidak pernah disentuh.
"""

import json
import sys

from config import settings
from fakes import FakeSnowflakeConnection
from snowflake import loader


class _NullLog:
    """Pengganti logger: tidak mencetak apa pun selama test."""

    def info(self, *args, **kwargs):
        pass

    def error(self, *args, **kwargs):
        pass


def _set_snowflake_settings(monkeypatch, value="dummy"):
    """Isi semua SF_* agar validate_snowflake() lolos."""
    for name in ["SF_ACCOUNT", "SF_USERNAME", "SF_PASSWORD", "SF_ROLE",
                 "SF_WAREHOUSE", "SF_DATABASE", "SF_SCHEMA"]:
        monkeypatch.setattr(settings, name, value)


# ---------- build_truncate_statement ----------

def test_build_truncate_statement():
    assert loader.build_truncate_statement("transactions") == (
        "TRUNCATE TABLE SPA_ANALYTICS.STAGING.transactions"
    )


# ---------- build_copy_statement ----------

def test_build_copy_statement_opsi_a():
    """Opsi A: stage menunjuk raw/, jadi COPY pakai @spa_stage/<table>/."""
    sql = loader.build_copy_statement("transactions")
    assert sql == (
        "COPY INTO SPA_ANALYTICS.STAGING.transactions "
        "FROM @spa_stage/transactions/ PATTERN='.*\\.csv' "
        "ON_ERROR='ABORT_STATEMENT'"
    )


# ---------- load_table: SUCCESS ----------

def test_load_table_success_urutan_sql_benar():
    conn = FakeSnowflakeConnection(count=179)
    record = loader.load_table(conn, "transactions", "batch_1", _NullLog())

    assert record["status"] == "SUCCESS"
    assert record["rows_loaded"] == 179
    assert record["source_table"] == "transactions"
    # urutan operasi: 1) TRUNCATE  2) COPY INTO  3) SELECT COUNT(*)
    assert conn.executed[0].startswith("TRUNCATE TABLE")
    assert conn.executed[1].startswith("COPY INTO")
    assert "SELECT COUNT(*)" in conn.executed[2]


# ---------- load_table: FAILED ----------

def test_load_table_gagal_mencatat_error_dan_lanjut():
    conn = FakeSnowflakeConnection(count=0, fail_on="COPY INTO")
    record = loader.load_table(conn, "transactions", "batch_1", _NullLog())

    assert record["status"] == "FAILED"
    assert "simulated error" in record["error_message"]
    assert "rows_loaded" not in record


# ---------- connect_snowflake: bootstrap filter ----------

def test_connect_snowflake_menyaring_param_kosong(monkeypatch):
    """Bootstrap: DB/WH/schema kosong harus dibuang dari params koneksi."""
    captured = {}

    class FakeConnectorModule:
        @staticmethod
        def connect(**params):
            captured.update(params)
            return "conn"

    fake_connector = FakeConnectorModule()
    import snowflake  # package lokal proyek ini

    # injeksi ke sys.modules + atribut parent, supaya `import snowflake.connector`
    # mengarah ke modul palsu ini
    monkeypatch.setitem(sys.modules, "snowflake.connector", fake_connector)
    monkeypatch.setattr(snowflake, "connector", fake_connector, raising=False)
    _set_snowflake_settings(monkeypatch, value="dummy")
    for name in ["SF_WAREHOUSE", "SF_DATABASE", "SF_SCHEMA"]:
        monkeypatch.setattr(settings, name, "")

    result = loader.connect_snowflake(require_objects=False)

    assert result == "conn"
    assert captured["account"] == "dummy"
    assert "warehouse" not in captured   # kosong -> dibuang
    assert "database" not in captured
    assert "schema" not in captured


# ---------- run_load: continue policy + metadata ----------

def test_run_load_error_policy_continue_memproses_semua(monkeypatch, tmp_path):
    """Mode 'continue': satu tabel gagal tidak menghentikan tabel lainnya."""
    monkeypatch.setattr(loader.logger, "LOGS_DIR", tmp_path)
    monkeypatch.setattr(loader.logger, "setup_logger",
                        lambda name="extract": _NullLog())
    monkeypatch.setattr(loader, "connect_snowflake",
                        lambda require_objects=False: FakeSnowflakeConnection(fail_on="COPY INTO"))
    monkeypatch.setattr(loader, "load_config",
                        lambda: {"tables": ["a", "b", "c"], "error_policy": "continue"})
    _set_snowflake_settings(monkeypatch)

    records = loader.run_load(batch_id="test_continue")

    assert len(records) == 3          # semua tabel tetap diproses
    assert all(r["status"] == "FAILED" for r in records)

    # metadata tertulis ke logs/load_log_<batch>.json
    log_path = tmp_path / "load_log_test_continue.json"
    assert log_path.exists()
    payload = json.loads(log_path.read_text())
    assert payload["batch_id"] == "test_continue"
    assert len(payload["tables"]) == 3
