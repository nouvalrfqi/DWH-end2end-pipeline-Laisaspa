"""Pipeline harian: Supabase -> S3 -> Snowflake STAGING -> dbt -> MART.

Menjalankan script project existing via subprocess memakai .env project.
"""

import os
import shutil
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

from airflow import DAG
from airflow.operators.python import PythonOperator
from dotenv import load_dotenv

PROJECT_ROOT = Path(os.getenv("SPA_PROJECT_ROOT", Path(__file__).resolve().parents[2]))
DBT_PROJECT_DIR = PROJECT_ROOT / "SPA_ANALYTICS_DBT"
PY_BIN = shutil.which("python") or "python"
DBT_BIN = shutil.which("dbt") or "dbt"


def run_pipeline(*cmd: str) -> None:
    load_dotenv(PROJECT_ROOT / ".env", override=True)
    subprocess.run(
        [str(c) for c in cmd],
        cwd=str(PROJECT_ROOT),
        env=os.environ.copy(),
        check=True,
    )

default_args = {
    "owner": "spa",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "start_date": datetime(2026, 9, 6),
}

with DAG(
    dag_id="spa_pipeline",
    default_args=default_args,
    schedule_interval="@daily",
    catchup=False,
    description="Extract Supabase -> S3 -> Snowflake STAGING -> dbt run/test",
    tags=["spa", "pipeline"],
) as dag:

    check_connectivity = PythonOperator(
        task_id="check_connectivity",
        python_callable=lambda: run_pipeline(PY_BIN, "main.py"),
    )
    extract_to_s3 = PythonOperator(
        task_id="extract_to_s3",
        python_callable=lambda: run_pipeline(PY_BIN, "-m", "extract.generic_extractor"),
    )
    load_to_staging = PythonOperator(
        task_id="load_to_staging",
        python_callable=lambda: run_pipeline(PY_BIN, "-m", "warehouse.loader", "--load"),
    )
    dbt_run = PythonOperator(
        task_id="dbt_run",
        python_callable=lambda: run_pipeline(DBT_BIN, "run", "--project-dir", DBT_PROJECT_DIR),
    )
    dbt_test = PythonOperator(
        task_id="dbt_test",
        python_callable=lambda: run_pipeline(DBT_BIN, "test", "--project-dir", DBT_PROJECT_DIR),
    )

    check_connectivity >> extract_to_s3 >> load_to_staging >> dbt_run >> dbt_test