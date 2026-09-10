"""Test doubles for the offline test suite.

Fakes mimic the behaviour of the real connectors (psycopg2 and
snowflake.connector) for just the subset the project uses, so tests run
fast, offline and deterministically.
"""


class FakeCursor:
    """Mimics psycopg2.cursor.

    Supports the API surface used by production code:
      - .description  -> list of (name, type_code) for SELECT *
      - .execute()    -> records the query for assertions
      - .fetchall()   -> returns the configured rows
      - .fetchone()   -> first row (used by COUNT(*))
      - context manager (production uses `with conn.cursor() as cur:`)
    """

    def __init__(self, rows=None, columns=None):
        self.description = [(name, None) for name in (columns or [])]
        self._rows = rows or []
        self.executed = None

    def execute(self, query, params=None):
        self.executed = (query, params)

    def fetchall(self):
        return self._rows

    def fetchone(self):
        return self._rows[0] if self._rows else None

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False


class FakeConnection:
    """Mimics psycopg2.connection (cursor() and close())."""

    def __init__(self, rows=None, columns=None):
        self._rows = rows
        self._columns = columns
        self.closed = False

    def cursor(self):
        return FakeCursor(rows=self._rows, columns=self._columns)

    def close(self):
        self.closed = True


class FakeSnowflakeCursor:
    """Mimics snowflake.connector.cursor for offline loader tests.

    - .execute()    -> records the query and optionally raises if it matches fail_on
    - .fetchone()   -> returns (count,) for SELECT COUNT(*)
    """

    def __init__(self, sink, count=0, fail_on=None):
        self._sink = sink
        self._count = count
        self._fail_on = fail_on

    def execute(self, query):
        self._sink.append(query)
        if self._fail_on and self._fail_on in query:
            raise RuntimeError("COPY INTO failed: simulated error")

    def fetchone(self):
        return (self._count,)

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False


class FakeSnowflakeConnection:
    """Mimics snowflake.connector.connection for offline loader tests."""

    def __init__(self, count=0, fail_on=None):
        self.executed = []
        self._count = count
        self._fail_on = fail_on
        self.closed = False

    def cursor(self):
        return FakeSnowflakeCursor(self.executed, self._count, self._fail_on)

    def close(self):
        self.closed = True