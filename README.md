# Modern Data Platform for Spa & Wellness

An end-to-end, production-style **modern data stack** that turns the operational data of a spa & wellness business into analytics-ready insights. This repository is an individual engineering showcase built to industry standards — from extraction and data quality gates, through a cloud data lake and warehouse, to governed, tested analytics marts.

## Overview

The platform moves operational data from a **Supabase PostgreSQL** (OLTP) source through a classic **ELT** pipeline:

```text
Supabase PostgreSQL (OLTP)
        │  11 business tables
        ▼
Python Generic Extraction Framework   ── extract + validate
        ▼
AWS S3 RAW Data Lake (CSV, date-partitioned)
        ▼
Snowflake STAGING → WAREHOUSE → MART  ── COPY INTO + dbt
        ▼
dbt (transformations + 72 data tests)
        ▼
Power BI / Streamlit
```

**Apache Airflow** (Docker Compose, Postgres backend) schedules and orchestrates the full pipeline on a `@daily` interval.

## Why this architecture

Each layer exists because it answers a specific engineering concern — and the decisions are deliberate:

| Concern | Choice | Rationale |
|---|---|---|
| **Extraction** | Generic, config-driven Python framework (`extract/`) | Adding a new table is a YAML change, not new code. No per-table extractors. |
| **Landing zone** | AWS S3 raw data lake, immutable CSV, date-partitioned | The lake decouples the OLTP source from the warehouse, keeps raw history, and lets Snowflake read data directly via internal staging. |
| **Loading (ELT, not ETL)** | Snowflake reads from S3 via `COPY INTO` | Byte movement happens inside the warehouse engine, not in Python. Python only triggers SQL and records batch metadata — a thin, testable runner. |
| **Transformations** | dbt (SQL-first) | Version-controlled, testable, dependency-managed transforms that run inside Snowflake. The warehouse, mart, and test layers are all declared in code. |
| **Orchestration** | Apache Airflow (LocalExecutor, Postgres backend) | Industry-standard scheduler with retries, backfill, and a monitored UI. Postgres (not SQLite) for production-grade state. |
| **Data quality** | Two gates: pre-upload validation + 72 dbt tests | Validation stops dirty data before it ever reaches S3; dbt tests guard the warehouse continuously (`not_null`, `unique`, `accepted_values`, row-count parity). |
| **Security** | Secrets only in `.env` (gitignored), least-privilege IAM | No credentials in code or history; `.env.example` ships placeholders only. |

The pipeline follows a **medallion-like layout** — `STAGING` (raw mirror) → `WAREHOUSE` (dimensional model) → `MART` (business-ready aggregates) — implemented in the dbt project under [`dbt/`](./dbt).

## Data Flow

### 1. Extract — Supabase → S3
The generic extractor reads `config/tables.yaml`, queries each of the **11 tables**, converts rows to a DataFrame, runs the validation suite, and uploads to a date-partitioned S3 key:

```text
raw/<table>/year=YYYY/month=MM/day=DD/<table>_<batch>.csv
```

- A failed validation **prevents the upload** — no dirty data enters the warehouse.
- Old objects under the table prefix are cleared before upload, so `STAGING` never accumulates duplicates across runs (idempotent full loads).
- Each batch writes a metadata manifest to `logs/extract_log_<batch>.json` for audit.

### 2. Load — S3 → Snowflake STAGING
`warehouse/loader.py` runs a full load per table:

```text
TRUNCATE TABLE STAGING.<table>
COPY INTO  STAGING.<table> FROM @spa_stage/<table>/ PATTERN='.*\.csv'
SELECT COUNT(*)   -- verify
```

Snowflake pulls from S3 through its own stage (`spa_stage`); per-table results and counts are recorded in `logs/load_log_<batch>.json`.

### 3. Transform — dbt STAGING → WAREHOUSE → MART
Declared models under [`dbt/models/`](./dbt/models):

- **Staging** — source declaration (`sources.yml`) of 7 tables from `SPA_ANALYTICS.STAGING`.
- **Warehouse** — dimensional core: `dim_date`, `dim_customer`, `dim_product`, `dim_treatment` and facts `fact_transactions`, `fact_completed_items`, `fact_treatment_activities`. Surrogate keys are stable hashes (e.g. `MD5(id)`) for safe incremental joins.
- **Mart** — analytics-ready aggregates: `mart_revenue_daily`, `mart_customer_analytics`, `mart_operations_booking`, `mart_product_analytics`, `mart_treatment_analytics`.
- **Data tests** — every primary/surrogate key is tested for `not_null` + `unique`; business enums use `accepted_values`. The suite currently runs **72/72 passing**.

### 4. Orchestrate — Apache Airflow
The `spa_pipeline` DAG chains five tasks:

```text
check_connectivity → extract_to_s3 → load_to_staging → dbt_run → dbt_test
```

Containerized with Docker Compose (`postgres`, `airflow-webserver`, `airflow-scheduler`, `airflow-init`), each task retries on failure (2×) and state is visible in the Airflow UI.

## Repository Structure

```text
spa-modern-data-platform/
├── airflow/                 # Airflow DAGs (Docker Compose orchestration)
├── config/                  # Central settings + table & validation YAML
├── dbt/                     # dbt project: STAGING sources, WAREHOUSE, MART, tests
├── extract/                 # Generic extractor + Postgres/S3 connectors
├── validation/              # Pre-upload data validation framework
├── warehouse/               # Snowflake loader, DDL generator, SQL scripts
├── utils/                   # Logging + batch metadata helpers
├── tests/                   # pytest suite (offline, mocked connectors)
├── scripts/                 # Operational utilities (e.g. connectivity check)
├── main.py                  # End-to-end connectivity acceptance check
├── docker-compose.yaml      # Airflow stack
├── Dockerfile               # Airflow image with project dependencies
├── requirements.txt
├── .env.example             # Placeholders only — never commit real secrets
└── README.md
```

## Getting Started

### Prerequisites

- Python 3.11+
- AWS account with the S3 bucket `spa-data-platform-dev` and a least-privilege IAM user
- Supabase project with the 11 source tables populated
- Snowflake account with a user allowed to run DDL
- dbt with a Snowflake profile for local runs

### Local setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env        # fill in real credentials (never commit .env)
python main.py              # verifies PostgreSQL + S3 connectivity
```

### Snowflake & dbt

1. Set `SNOWFLAKE_*` variables in `.env` (account identifier, user, password, role, warehouse, database, schema).
2. Create the foundation objects and the external stage:

   ```bash
   python -m warehouse.loader --setup
   ```

3. Load staging data (full load, per table):

   ```bash
   python -m warehouse.loader --load
   ```

4. Configure a dbt profile named `dbt` (e.g. in `~/.dbt/profiles.yml`) pointing at the same Snowflake account, then run the dbt project under [`dbt/`](./dbt):

   ```bash
   cd dbt
   dbt deps
   dbt run
   dbt test
   ```

> The dbt project name/profile is `dbt`. If you upgraded from an older iteration, rename the profile key in your local `profiles.yml` accordingly.

> The S3 → Snowflake stage uses direct AWS credentials injected at runtime during `--setup` (an explicit workaround chosen over a storage integration after diagnosing an `sts:AssumeRole` restriction between Snowflake and this AWS account).

## Testing

The repository ships a **comprehensive offline pytest suite** (`tests/`) covering settings, connectors, the generic extractor, the validation framework, the Snowflake SQL builders, and the DDL generator — using fakes and `moto` so nothing needs a live account:

```bash
pytest
```

CI can run this suite without any environment credentials.

## Security

- All credentials live in local `.env` files, which are gitignored; `.env.example` holds placeholders only.
- Production code reads credentials exclusively from environment variables — never hardcoded.
- S3 bucket blocks public access with server-side encryption; AWS IAM follows least privilege.
- `*.pem`/key material is explicitly gitignored.

## Status & Roadmap

| Phase | Scope | Status |
|---|---|---|
| 0 | Business & analytics design (KPIs, source mapping, star schema) | Done |
| 1–2 | Cloud infrastructure & connectivity | Done |
| 3 | Generic extraction framework | Done |
| 4 | Data validation framework | Done |
| 5 | Snowflake staging (DDL, loader, COPY INTO load) | Done |
| 6–8 | Dimensional warehouse + dbt marts + data tests | Done |
| 9 | Power BI / Streamlit visualisation | In progress |
| 10–12 | Airflow orchestration, incremental loading, CI/CD | Done / In progress |
| 13–15 | Monitoring, observability, hardening | Planned |