"""Snowflake connectivity check.

Connects using only the NON-EMPTY SNOWFLAKE_* settings so it also works in
"bootstrap" mode — before `--setup` has created SPA_WH / SPA_ANALYTICS
(warehouse/database/schema empty in .env).

Usage:
    python scripts/check_snowflake.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import settings


def check_snowflake() -> bool:
    try:
        import snowflake.connector
    except ImportError as exc:
        print(f"FAIL snowflake: snowflake-connector-python not installed ({exc})")
        return False

    params = {k: v for k, v in settings.snowflake_conn_params().items() if v}
    if not params:
        print("FAIL snowflake: no SNOWFLAKE_* settings configured in .env")
        return False

    try:
        conn = snowflake.connector.connect(**params)
        with conn.cursor() as cur:
            cur.execute(
                "SELECT CURRENT_ACCOUNT(), CURRENT_USER(),"
                " CURRENT_ROLE(), CURRENT_WAREHOUSE()"
            )
            account, user, role, warehouse = cur.fetchone()
        conn.close()
    except Exception as exc:
        print(f"FAIL snowflake: {exc}")
        return False

    print("PASS snowflake: connected")
    print(f"  account   = {account}")
    print(f"  user      = {user}")
    print(f"  role      = {role}")
    print(f"  warehouse = {warehouse or '(none — expected before --setup)'}")
    return True


if __name__ == "__main__":
    ok = check_snowflake()
    print()
    if ok:
        print("Snowflake connectivity: PASS")
        sys.exit(0)
    print("Snowflake connectivity: FAIL")
    sys.exit(1)
