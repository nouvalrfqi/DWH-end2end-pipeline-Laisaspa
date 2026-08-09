"""Test doubles (fakes) untuk suite Sprint 4.

Fake meniru PERILAKU objek asli, bukan implementasinya. Kita hanya meniru
bagian psycopg2 yang benar-benar dipakai proyek ini, supaya test bisa
berjalan offline, cepat, dan hasilnya deterministik.
"""


class FakeCursor:
    """Meniru psycopg2.cursor.

    Yang dipakai kode produksi:
      - .description        -> list (column_name, type_code) untuk SELECT *
      - .execute(query)     -> menyimpan query, agar test bisa meng-assert
      - .fetchall()         -> mengembalikan baris yang dikonfigurasi
      - .fetchone()         -> baris pertama (dipakai COUNT(*))
      - __enter__/__exit__  -> kode produksi memakai `with conn.cursor() as cur:`
    """

    def __init__(self, rows=None, columns=None):
        self.description = [(name, None) for name in (columns or [])]
        self._rows = rows or []
        self.executed = None  # (query, params) terakhir, untuk assert

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
    """Meniru psycopg2.connection.

    Kode produksi memakai conn.cursor() dan conn.close().
    Setiap panggilan cursor() mengembalikan FakeCursor baru.
    """

    def __init__(self, rows=None, columns=None):
        self._rows = rows
        self._columns = columns
        self.closed = False

    def cursor(self):
        return FakeCursor(rows=self._rows, columns=self._columns)

    def close(self):
        self.closed = True
