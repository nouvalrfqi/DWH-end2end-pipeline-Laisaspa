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


def test_snowflake_conn_params_memiliki_semua_key_connector():
    """Kontrak: params Snowflake selalu berisi key yang dibutuhkan connector."""
    params = settings.snowflake_conn_params()
    for key in ["account", "user", "password", "role",
                "warehouse", "database", "schema"]:
        assert key in params


def test_snowflake_conn_params_mengikuti_env(monkeypatch):
    """Nilai param diambil dari env SNOWFLAKE_*."""
    monkeypatch.setattr(settings, "SF_ACCOUNT", "acct-1")
    monkeypatch.setattr(settings, "SF_USERNAME", "user1")
    monkeypatch.setattr(settings, "SF_PASSWORD", "pass1")
    monkeypatch.setattr(settings, "SF_ROLE", "ACCOUNTADMIN")

    params = settings.snowflake_conn_params()
    assert params["account"] == "acct-1"
    assert params["user"] == "user1"
    assert params["password"] == "pass1"
    assert params["role"] == "ACCOUNTADMIN"


def test_validate_snowflake_passes_saat_semua_terisi(monkeypatch):
    """Jika semua env Snowflake terisi, validate_snowflake() tidak boleh error."""
    for name in ["SF_ACCOUNT", "SF_USERNAME", "SF_PASSWORD", "SF_ROLE",
                 "SF_WAREHOUSE", "SF_DATABASE", "SF_SCHEMA"]:
        monkeypatch.setattr(settings, name, "dummy")

    settings.validate_snowflake()  # kalau ini melempar, test otomatis gagal


def test_validate_snowflake_raises_saat_hilang(monkeypatch):
    """Fail-fast: env Snowflake kosong harus memunculkan RuntimeError jelas."""
    for name in ["SF_ACCOUNT", "SF_USERNAME", "SF_PASSWORD", "SF_ROLE",
                 "SF_WAREHOUSE", "SF_DATABASE", "SF_SCHEMA"]:
        monkeypatch.setattr(settings, name, "")

    with pytest.raises(RuntimeError, match="Missing required environment variables"):
        settings.validate_snowflake()
