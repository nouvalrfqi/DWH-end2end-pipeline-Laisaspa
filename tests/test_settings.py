"""Test untuk config/settings.py.

Goal: memastikan konfigurasi proyek dibaca benar dan "fail-fast" terjadi
ketika ada env var penting yang hilang.
"""

import pytest

from config import settings


def test_pg_conn_params_memiliki_semua_key_yang_dibutuhkan_psycopg2():
    """Kunci kontrak: settings harus selalu menghasilkan param koneksi lengkap."""
    params = settings.pg_conn_params()
    for key in ["host", "port", "dbname", "user", "password",
                "sslmode", "connect_timeout"]:
        assert key in params


def test_pg_conn_params_default_sslmode_require():
    """Supabase mewajibkan SSL, jadi default harus 'require'."""
    assert settings.pg_conn_params()["sslmode"] == "require"


def test_validate_passes_saat_semua_required_terisi(monkeypatch):
    """Jika semua env penting ada, validate() tidak boleh melempar error."""
    monkeypatch.setattr(settings, "PG_HOST", "dummy")
    monkeypatch.setattr(settings, "PG_USERNAME", "dummy")
    monkeypatch.setattr(settings, "PG_PASSWORD", "dummy")
    monkeypatch.setattr(settings, "S3_BUCKET", "dummy")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "dummy")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "dummy")

    settings.validate()  # kalau ini melempar, test otomatis gagal


def test_validate_raises_saat_required_hilang(monkeypatch):
    """Fail-fast: kalau ada env penting kosong, harus error dengan pesan jelas."""
    monkeypatch.setattr(settings, "PG_HOST", "")
    monkeypatch.setattr(settings, "PG_USERNAME", "")
    monkeypatch.setattr(settings, "PG_PASSWORD", "")
    monkeypatch.setattr(settings, "S3_BUCKET", "")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "")

    with pytest.raises(RuntimeError, match="Missing required environment variables"):
        settings.validate()


def test_source_tables_berisi_11_tabel():
    """Kontrak awal proyek: 11 tabel sumber dari PRD."""
    assert len(settings.SOURCE_TABLES) == 11
    assert "transactions" in settings.SOURCE_TABLES
