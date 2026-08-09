"""Test untuk validation/validators.py.

Goal: memastikan setiap aturan validasi (schema, null, duplicate, range,
accepted value, row count) berperilaku benar — PASS saat data baik, FAIL saat
data melanggar, dan SKIPPED saat tidak dikonfigurasi.
"""

import pandas as pd

from validation import validators


def _df(columns, rows):
    """Helper kecil: bikin DataFrame dari daftar kolom dan baris."""
    return pd.DataFrame(rows, columns=columns)


# ---------- columns (schema check) ----------

def test_validate_columns_pass():
    df = _df(["id", "name"], [[1, "a"]])
    assert validators.validate_columns(df, ["id", "name"])["status"] == "PASS"


def test_validate_columns_missing():
    df = _df(["id"], [[1]])
    assert validators.validate_columns(df, ["id", "name"])["status"] == "FAIL"


def test_validate_columns_unexpected():
    df = _df(["id", "name", "extra"], [[1, "a", "x"]])
    assert validators.validate_columns(df, ["id", "name"])["status"] == "FAIL"


# ---------- not_null ----------

def test_validate_not_null_pass():
    df = _df(["id", "name"], [[1, "a"], [2, "b"]])
    assert validators.validate_not_null(df, ["id", "name"])["status"] == "PASS"


def test_validate_not_null_fail():
    df = _df(["id", "name"], [[1, None]])
    assert validators.validate_not_null(df, ["name"])["status"] == "FAIL"


# ---------- unique (duplicate detection) ----------

def test_validate_unique_pass():
    df = _df(["id"], [[1], [2]])
    assert validators.validate_unique(df, ["id"])["status"] == "PASS"


def test_validate_unique_duplicate():
    df = _df(["id"], [[1], [1]])
    assert validators.validate_unique(df, ["id"])["status"] == "FAIL"


def test_validate_unique_skipped_kalau_tidak_dikonfigurasi():
    assert validators.validate_unique(pd.DataFrame(), [])["status"] == "SKIPPED"


# ---------- min_value ----------

def test_validate_min_value_pass():
    df = _df(["price"], [[0], [10]])
    assert validators.validate_min_value(df, "price", 0)["status"] == "PASS"


def test_validate_min_value_fail():
    df = _df(["price"], [[-1], [10]])
    assert validators.validate_min_value(df, "price", 0)["status"] == "FAIL"


def test_validate_min_value_column_hilang():
    df = _df(["price"], [[1]])
    assert validators.validate_min_value(df, "total", 0)["status"] == "FAIL"


# ---------- accepted_values ----------

def test_validate_accepted_values_pass():
    df = _df(["rating"], [[1], [5]])
    assert validators.validate_accepted_values(df, "rating",
                                               [1, 2, 3, 4, 5])["status"] == "PASS"


def test_validate_accepted_values_fail():
    df = _df(["rating"], [[6]])  # rating 6 di luar rentang 1-5
    assert validators.validate_accepted_values(df, "rating",
                                               [1, 2, 3, 4, 5])["status"] == "FAIL"


# ---------- row_count ----------

def test_validate_row_count_pass():
    assert validators.validate_row_count(5, 5)["status"] == "PASS"


def test_validate_row_count_fail():
    assert validators.validate_row_count(5, 4)["status"] == "FAIL"


# ---------- agregasi run_table_validation ----------

def test_run_table_validation_skipped_tanpa_rules():
    r = validators.run_table_validation("treatments", pd.DataFrame(), None, 0)
    assert r["overall"] == "SKIPPED"


def test_run_table_validation_pass():
    rules = {
        "columns": ["id", "price"],
        "not_null": ["id"],
        "unique": ["id"],
        "checks": [{"type": "min_value", "column": "price", "min": 0}],
    }
    df = _df(["id", "price"], [[1, 100], [2, 50]])
    r = validators.run_table_validation("x", df, rules, 2)
    assert r["overall"] == "PASS"


def test_run_table_validation_fail_satu_check_gagal():
    rules = {
        "columns": ["id", "price"],
        "checks": [{"type": "min_value", "column": "price", "min": 0}],
    }
    df = _df(["id", "price"], [[1, -5]])
    r = validators.run_table_validation("x", df, rules, 1)
    assert r["overall"] == "FAIL"


def test_run_table_validation_unknown_rule_type_dianggap_fail():
    """Aturan tak dikenal harus FAIL, bukan diam-diam di-skip."""
    rules = {
        "columns": ["id"],
        "checks": [{"type": "mystery", "column": "id"}],
    }
    df = _df(["id"], [[1]])
    r = validators.run_table_validation("x", df, rules, 1)
    assert r["overall"] == "FAIL"
