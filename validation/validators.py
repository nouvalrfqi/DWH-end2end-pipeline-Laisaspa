"""Data validation framework.

Validates extracted DataFrames against rules in config/validation_rules.yaml.
Every check returns a dict {"name", "status", "detail"}; run_table_validation
aggregates them into {"overall", "checks"}.
"""

from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
import yaml

RULES_PATH = Path("config/validation_rules.yaml")

_rules_cache: Optional[Dict] = None


def load_rules(path: Path = RULES_PATH) -> dict:
    """Load validation rules (cached after first read)."""
    global _rules_cache
    if _rules_cache is None:
        with open(path, "r") as f:
            _rules_cache = yaml.safe_load(f)
    return _rules_cache


def _result(name: str, status: str, detail: str = "") -> Dict:
    return {"name": name, "status": status, "detail": detail}


def validate_columns(df: pd.DataFrame, expected: List[str]) -> Dict:
    """Schema check: expected columns exactly match actual columns."""
    actual = set(df.columns)
    expected_set = set(expected)
    missing = sorted(expected_set - actual)
    unexpected = sorted(actual - expected_set)
    if missing or unexpected:
        detail = f"missing={missing} unexpected={unexpected}"
        return _result("columns", "FAIL", detail)
    return _result("columns", "PASS", f"{len(expected)} columns match")


def validate_not_null(df: pd.DataFrame, columns: List[str]) -> Dict:
    """Null check: required columns must not contain nulls."""
    null_cols = [col for col in columns if col in df.columns and df[col].isna().any()]
    if null_cols:
        return _result("not_null", "FAIL", f"nulls found in {null_cols}")
    return _result("not_null", "PASS", "no nulls in required columns")


def validate_unique(df: pd.DataFrame, columns: List[str]) -> Dict:
    """PK uniqueness check (detects duplicates)."""
    if not columns:
        return _result("unique", "SKIPPED", "no unique columns configured")
    if df.duplicated(subset=columns).any():
        return _result("unique", "FAIL", f"duplicates in {columns}")
    return _result("unique", "PASS", f"{columns} unique")


def validate_min_value(df: pd.DataFrame, column: str, min_value: float) -> Dict:
    """Numeric range check: all non-null values >= min_value."""
    if column not in df.columns:
        return _result(f"min_value.{column}", "FAIL", f"column {column} missing")
    bad = df[column].dropna() < min_value
    if bad.any():
        count = int(bad.sum())
        return _result(f"min_value.{column}", "FAIL", f"{count} rows < {min_value}")
    return _result(f"min_value.{column}", "PASS", f"all >= {min_value}")


def validate_accepted_values(df: pd.DataFrame, column: str, values: List) -> Dict:
    """Accepted-value check: every non-null value is within `values`."""
    if column not in df.columns:
        return _result(f"accepted_values.{column}", "FAIL", f"column {column} missing")
    bad = ~df[column].dropna().isin(values)
    if bad.any():
        count = int(bad.sum())
        return _result(f"accepted_values.{column}", "FAIL", f"{count} rows outside {values}")
    return _result(f"accepted_values.{column}", "PASS", "all values accepted")


def validate_row_count(source_count: int, extracted_count: int) -> Dict:
    """Row-count check: PostgreSQL COUNT(*) vs extracted row count."""
    if source_count != extracted_count:
        detail = f"source={source_count} extracted={extracted_count}"
        return _result("row_count", "FAIL", detail)
    return _result("row_count", "PASS", f"{source_count} rows match")


def run_table_validation(table: str, df: pd.DataFrame, rules: Optional[dict],
                         source_count: int) -> Dict:
    """Run all configured checks for a table.

    Returns {"overall": "PASS" | "FAIL" | "SKIPPED", "checks": [...]}.
    """
    if not rules:
        return {"overall": "SKIPPED", "checks": []}

    checks: List[Dict] = []
    checks.append(validate_columns(df, rules.get("columns", [])))
    checks.append(validate_row_count(source_count, len(df)))

    not_null = rules.get("not_null", [])
    if not_null:
        checks.append(validate_not_null(df, not_null))

    unique = rules.get("unique", [])
    if unique:
        checks.append(validate_unique(df, unique))

    for rule in rules.get("checks", []):
        rtype = rule.get("type")
        if rtype == "min_value":
            checks.append(validate_min_value(df, rule["column"], rule["min"]))
        elif rtype == "accepted_values":
            checks.append(validate_accepted_values(df, rule["column"], rule["values"]))
        else:
            checks.append(_result(f"unknown_check.{rtype}", "FAIL", "unknown rule type"))

    overall = "PASS" if all(c["status"] == "PASS" for c in checks) else "FAIL"
    return {"overall": overall, "checks": checks}
