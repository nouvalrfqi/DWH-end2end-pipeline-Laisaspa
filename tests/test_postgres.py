"""Test untuk extract/postgres_connector.py dengan psycopg2 di-mock.

Goal: menguji LOGIKA koneksi kita (retry/backoff, error handling, query)
tanpa database sungguhan.
"""

import psycopg2
import pytest

from extract import postgres_connector
from fakes import FakeConnection


def test_connect_returns_connection_saat_sukses(monkeypatch):
    """Jika psycopg2.connect berhasil, kita terima apa adanya."""
    fake = FakeConnection()
    monkeypatch.setattr(postgres_connector.psycopg2, "connect",
                        lambda **kw: fake)

    assert postgres_connector.connect() is fake


def test_connect_raises_setelah_max_retries(monkeypatch):
    """Jika gagal terus-menerus, kita harus menyerah dengan RuntimeError.

    time.sleep di-patch supaya test tidak benar-benar menunggu 2+4+... detik.
    """
    calls = {"n": 0}

    def always_fail(**kw):
        calls["n"] += 1
        raise psycopg2.OperationalError("db down")

    monkeypatch.setattr(postgres_connector.psycopg2, "connect", always_fail)
    monkeypatch.setattr("time.sleep", lambda s: None)

    with pytest.raises(RuntimeError, match="Could not connect to PostgreSQL"):
        postgres_connector.connect(max_retries=2)

    assert calls["n"] == 2  # tepat 2 percobaan, tidak lebih


def test_connect_sukses_setelah_retry(monkeypatch):
    """Gagal 2x lalu sukses -> harus berhasil di percobaan ke-3."""
    calls = {"n": 0}
    fake = FakeConnection()

    def flaky(**kw):
        calls["n"] += 1
        if calls["n"] < 3:
            raise psycopg2.OperationalError("transient")
        return fake

    monkeypatch.setattr(postgres_connector.psycopg2, "connect", flaky)
    monkeypatch.setattr("time.sleep", lambda s: None)

    assert postgres_connector.connect(max_retries=3) is fake
    assert calls["n"] == 3


def test_fetch_row_count_mengembalikan_angka():
    """COUNT(*) harus mengembalikan baris pertama dari query (angka)."""
    conn = FakeConnection(rows=[(179,)])

    assert postgres_connector.fetch_row_count(conn, "transactions") == 179


def test_inspect_table_mengembalikan_daftar_kolom():
    """inspect_table harus mengembalikan list (column_name, data_type)."""
    expected = [("id", "uuid"), ("name", "text")]
    conn = FakeConnection(rows=expected)

    assert postgres_connector.inspect_table(conn, "treatments") == expected
