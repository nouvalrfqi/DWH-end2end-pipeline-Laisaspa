"""Test untuk extract/generic_extractor.py.

Goal: menguji bagian inti pipeline — build key S3, baca konfigurasi, dan
perilaku extract_table (sukses / validasi gagal / error). Semua dependensi
eksternal (Postgres & S3) di-mock supaya offline & deterministik.
"""

from datetime import datetime

from extract import generic_extractor, postgres_connector, s3_client
from fakes import FakeConnection


class _NullLog:
    """Pengganti logger: tidak mencetak apa pun selama test."""
    def info(self, *args, **kwargs):
        pass

    def error(self, *args, **kwargs):
        pass


# ---------- helper ----------

def _run_extract_table(monkeypatch, conn, rows, columns, validation_overall="PASS"):
    """Setup mock yang dipakai beberapa test extract_table."""
    monkeypatch.setattr(postgres_connector, "fetch_row_count",
                        lambda c, t: len(rows))
    monkeypatch.setattr(
        generic_extractor.validators, "run_table_validation",
        lambda t, df, r, src: {
            "overall": validation_overall,
            "checks": [{"name": "dummy", "status": validation_overall}],
        },
    )

    now = datetime(2026, 8, 9, 2, 30, 0)
    return generic_extractor.extract_table(
        conn, "treatments", "20260809_023000", now, _NullLog(), rules={}
    )


# ---------- build_s3_key ----------

def test_build_s3_key_partisi_berdasarkan_tanggal_ingestion():
    """Key harus mengikuti format raw/<table>/year=/month=/day=..."""
    now = datetime(2026, 8, 9, 2, 30, 0)
    key = generic_extractor.build_s3_key("transactions", "20260809_023000", now)

    assert key == ("raw/transactions/year=2026/month=08/day=09/"
                   "transactions_20260809_023000.csv")


# ---------- load_config ----------

def test_load_config_mengembalikan_daftar_tabel():
    """Konfigurasi YAML harus terbaca dan memuat daftar tabel."""
    config = generic_extractor.load_config()
    assert "tables" in config
    assert "transactions" in config["tables"]


# ---------- extract_table: SUCCESS ----------

def test_extract_table_success_mengupload_file(monkeypatch):
    rows = [[1, "Massage", 150000], [2, "Facial", 200000]]
    columns = ["id", "name", "price"]
    conn = FakeConnection(rows=rows, columns=columns)

    uploaded = {}
    monkeypatch.setattr(s3_client, "upload_bytes",
                        lambda key, body, client=None: uploaded.update(key=key, body=body))

    record = _run_extract_table(monkeypatch, conn, rows, columns)

    assert record["status"] == "SUCCESS"
    assert record["rows_extracted"] == 2
    assert record["rows_loaded"] == 2
    assert record["file_path"].endswith("treatments_20260809_023000.csv")
    assert uploaded["key"] == record["file_path"]  # file yang di-upload = path yang dicatat


# ---------- extract_table: VALIDATION FAIL (tidak upload) ----------

def test_extract_table_tidak_mengupload_saat_validasi_gagal(monkeypatch):
    rows = [[1, "Massage", -5]]
    columns = ["id", "name", "price"]
    conn = FakeConnection(rows=rows, columns=columns)

    called = {"n": 0}
    monkeypatch.setattr(s3_client, "upload_bytes",
                        lambda key, body, client=None: called.update(n=called["n"] + 1))

    record = _run_extract_table(monkeypatch, conn, rows, columns,
                                validation_overall="FAIL")

    assert record["status"] == "VALIDATION_FAILED"
    assert record["rows_loaded"] == 0
    assert called["n"] == 0            # bukti: upload TIDAK pernah dipanggil
    assert "validation failed" in record["error_message"]


# ---------- extract_table: exception ----------

def test_extract_table_mencatat_error_saat_exception(monkeypatch):
    conn = FakeConnection(rows=[], columns=["id"])

    def boom(c, t):
        raise RuntimeError("database went away")

    monkeypatch.setattr(postgres_connector, "fetch_row_count", boom)

    record = generic_extractor.extract_table(
        conn, "treatments", "20260809_023000", datetime(2026, 8, 9, 2, 30, 0),
        _NullLog(), rules={}
    )

    assert record["status"] == "FAILED"
    assert record["error_message"] == "database went away"


# ---------- run(): error_policy ----------

def test_run_error_policy_continue_memproses_semua(monkeypatch):
    """Mode 'continue': satu tabel gagal tidak menghentikan tabel lainnya."""
    monkeypatch.setattr(generic_extractor.postgres_connector, "connect",
                        lambda **kw: FakeConnection(rows=[], columns=["id"]))
    monkeypatch.setattr(generic_extractor.postgres_connector, "fetch_row_count",
                        lambda c, t: 0)
    monkeypatch.setattr(generic_extractor, "extract_table",
                        lambda *a, **k: {"status": "FAILED"})
    monkeypatch.setattr(generic_extractor.logger, "setup_logger",
                        lambda name="extract": _NullLog())
    monkeypatch.setattr(generic_extractor.logger, "write_batch_metadata",
                        lambda b, r: None)
    monkeypatch.setattr(generic_extractor, "load_config",
                        lambda: {"tables": ["a", "b", "c"], "error_policy": "continue"})

    records = generic_extractor.run(batch_id="test_continue")

    assert len(records) == 3  # semua tabel tetap diproses meski gagal


def test_run_error_policy_stop_berhenti_saat_gagal(monkeypatch):
    """Mode 'stop': kegagalan pertama langsung menghentikan sisa tabel."""
    count = {"n": 0}

    def failing(*a, **k):
        count["n"] += 1
        return {"status": "FAILED"}

    monkeypatch.setattr(generic_extractor.postgres_connector, "connect",
                        lambda **kw: FakeConnection(rows=[], columns=["id"]))
    monkeypatch.setattr(generic_extractor.postgres_connector, "fetch_row_count",
                        lambda c, t: 0)
    monkeypatch.setattr(generic_extractor, "extract_table", failing)
    monkeypatch.setattr(generic_extractor.logger, "setup_logger",
                        lambda name="extract": _NullLog())
    monkeypatch.setattr(generic_extractor.logger, "write_batch_metadata",
                        lambda b, r: None)
    monkeypatch.setattr(generic_extractor, "load_config",
                        lambda: {"tables": ["a", "b", "c"], "error_policy": "stop"})

    records = generic_extractor.run(batch_id="test_stop")

    assert len(records) == 1   # hanya 1 record, sisanya dihentikan
    assert count["n"] == 1     # extract_table hanya dipanggil sekali
