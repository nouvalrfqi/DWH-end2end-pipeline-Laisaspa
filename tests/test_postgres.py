"""Tests for extract/postgres_connector.py with psycopg2 mocked.

Verifies the connection logic (retry/backoff, error handling, queries)
without a real database.
"""

import psycopg2
import pytest

from extract import postgres_connector
from fakes import FakeConnection


def test_connect_returns_connection_on_success(monkeypatch):
    """When psycopg2.connect succeeds, return it untouched."""
    fake = FakeConnection()
    monkeypatch.setattr(postgres_connector.psycopg2, "connect",
                        lambda **kw: fake)

    assert postgres_connector.connect() is fake


def test_connect_raises_after_max_retries(monkeypatch):
    """Give up with a RuntimeError after exhausting all retries.

    time.sleep is patched so the test does not wait 2+4+... seconds.
    """
    calls = {"n": 0}

    def always_fail(**kw):
        calls["n"] += 1
        raise psycopg2.OperationalError("db down")

    monkeypatch.setattr(postgres_connector.psycopg2, "connect", always_fail)
    monkeypatch.setattr("time.sleep", lambda s: None)

    with pytest.raises(RuntimeError, match="Could not connect to PostgreSQL"):
        postgres_connector.connect(max_retries=2)

    assert calls["n"] == 2  # exactly 2 attempts, no more


def test_connect_succeeds_after_retry(monkeypatch):
    """Fail twice then succeed -> must succeed on the 3rd attempt."""
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


def test_fetch_row_count_returns_number():
    """COUNT(*) must return the first row of the query (a number)."""
    conn = FakeConnection(rows=[(179,)])

    assert postgres_connector.fetch_row_count(conn, "transactions") == 179


def test_inspect_table_returns_column_list():
    """inspect_table must return a list of (column_name, data_type)."""
    expected = [("id", "uuid"), ("name", "text")]
    conn = FakeConnection(rows=expected)

    assert postgres_connector.inspect_table(conn, "treatments") == expected