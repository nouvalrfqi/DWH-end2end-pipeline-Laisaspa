"""Tests for config/settings.py.

Verifies the project configuration is read correctly and fails fast when
important environment variables are missing.
"""

import pytest

from config import settings


def test_pg_conn_params_contains_all_psycopg2_keys():
    """Contract: settings must always produce a complete connection params."""
    params = settings.pg_conn_params()
    for key in ["host", "port", "dbname", "user", "password",
                "sslmode", "connect_timeout"]:
        assert key in params


def test_pg_conn_params_default_sslmode_require():
    """Supabase requires SSL, so the default must be 'require'."""
    assert settings.pg_conn_params()["sslmode"] == "require"


def test_validate_passes_when_required_are_set(monkeypatch):
    """validate() must not raise when every required env is present."""
    monkeypatch.setattr(settings, "PG_HOST", "dummy")
    monkeypatch.setattr(settings, "PG_USERNAME", "dummy")
    monkeypatch.setattr(settings, "PG_PASSWORD", "dummy")
    monkeypatch.setattr(settings, "S3_BUCKET", "dummy")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "dummy")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "dummy")

    settings.validate()  # the test fails automatically if this raises


def test_validate_raises_when_required_missing(monkeypatch):
    """Fail fast: a missing env must produce a clear error message."""
    monkeypatch.setattr(settings, "PG_HOST", "")
    monkeypatch.setattr(settings, "PG_USERNAME", "")
    monkeypatch.setattr(settings, "PG_PASSWORD", "")
    monkeypatch.setattr(settings, "S3_BUCKET", "")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "")

    with pytest.raises(RuntimeError, match="Missing required environment variables"):
        settings.validate()


def test_source_tables_contain_11_tables():
    """Initial project contract: 11 source tables."""
    assert len(settings.SOURCE_TABLES) == 11
    assert "transactions" in settings.SOURCE_TABLES


def test_snowflake_conn_params_contains_all_connector_keys():
    """Contract: Snowflake params always contain the connector keys."""
    params = settings.snowflake_conn_params()
    for key in ["account", "user", "password", "role",
                "warehouse", "database", "schema"]:
        assert key in params


def test_snowflake_conn_params_follow_env(monkeypatch):
    """Param values come from the SNOWFLAKE_* environment."""
    monkeypatch.setattr(settings, "SF_ACCOUNT", "acct-1")
    monkeypatch.setattr(settings, "SF_USERNAME", "user1")
    monkeypatch.setattr(settings, "SF_PASSWORD", "pass1")
    monkeypatch.setattr(settings, "SF_ROLE", "ACCOUNTADMIN")

    params = settings.snowflake_conn_params()
    assert params["account"] == "acct-1"
    assert params["user"] == "user1"
    assert params["password"] == "pass1"
    assert params["role"] == "ACCOUNTADMIN"


def test_validate_snowflake_passes_when_all_set(monkeypatch):
    """validate_snowflake() must not raise when every snowflake env is set."""
    for name in ["SF_ACCOUNT", "SF_USERNAME", "SF_PASSWORD", "SF_ROLE",
                 "SF_WAREHOUSE", "SF_DATABASE", "SF_SCHEMA"]:
        monkeypatch.setattr(settings, name, "dummy")

    settings.validate_snowflake()  # the test fails automatically if this raises


def test_validate_snowflake_raises_when_missing(monkeypatch):
    """Fail fast: empty Snowflake env must raise a clear RuntimeError."""
    for name in ["SF_ACCOUNT", "SF_USERNAME", "SF_PASSWORD", "SF_ROLE",
                 "SF_WAREHOUSE", "SF_DATABASE", "SF_SCHEMA"]:
        monkeypatch.setattr(settings, name, "")

    with pytest.raises(RuntimeError, match="Missing required environment variables"):
        settings.validate_snowflake()