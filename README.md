# Modern Data Platform for Spa & Wellness Business

An end-to-end modern data engineering portfolio project that extracts operational data from a
Supabase PostgreSQL (OLTP) source, lands immutable raw data into an AWS S3 Data Lake, loads and
models analytical data in Snowflake, transforms and tests it with dbt, orchestrates scheduled
workflows with Apache Airflow, and exposes business-ready data marts to Power BI.

> Full specification: [`Modern_Data_Platform_Spa_TDD.md`](./Modern_Data_Platform_Spa_TDD.md)

## Architecture

```text
Supabase PostgreSQL (OLTP)
        |
        v
Python Generic Extraction Framework
        |
        v
AWS S3 RAW Data Lake (CSV -> Parquet)
        |
        v
Snowflake STAGING -> WAREHOUSE -> MART
        |
        v
dbt Transformation
        |
        v
Power BI
```

Apache Airflow (Docker Compose) orchestrates and schedules the full pipeline.

## Tech Stack

| Layer | Technology |
|---|---|
| Source | Supabase PostgreSQL |
| Extraction | Python (psycopg2, pandas) |
| Data Lake | AWS S3 (boto3) |
| Warehouse | Snowflake |
| Transformation | dbt |
| Orchestration | Apache Airflow (Docker) |
| BI | Power BI |
| CI/CD | GitHub Actions |

## Repository Structure

```text
spa-modern-data-platform/
|-- .github/workflows/     # CI/CD (future)
|-- config/                # settings + table/validation YAML config
|-- extract/               # generic extractor, connectors
|-- upload/                # S3 upload helpers
|-- utils/                 # shared utilities (logging, etc.)
|-- validation/            # data validation framework
|-- snowflake/             # SQL scripts (future)
|-- dbt/                   # dbt project (future)
|-- airflow/               # DAGs (future)
|-- tests/                 # pytest suite
|-- docs/                  # business & technical documentation
|-- logs/                  # extraction logs (gitignored)
|-- requirements.txt
|-- .env.example
|-- .gitignore
|-- docker-compose.yml     # (future)
|-- README.md
```

## Prerequisites

- Python 3.11+
- AWS account with S3 bucket `spa-data-platform-dev` (least-privilege IAM user)
- Supabase project with the source tables populated

## Setup

```bash
# 1. Clone / enter the repository
cd spa-modern-data-platform

# 2. Create a virtual environment
python -m venv .venv
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
#   -> fill in real Supabase / AWS credentials (never commit .env)

# 5. Verify connectivity to Supabase
python main.py
```

## Environment Variables

See [`.env.example`](./.env.example) for the full list. Keep all credentials in `.env`
and never commit secrets to Git.

## Roadmap / Status

| Phase | Scope | Status |
|---|---|---|
| 0 | Business & design (KPI, source mapping, star schema) | Done |
| 1-2 | Cloud infra + connectivity | In progress |
| 3 | Generic extraction framework | Next |
| 4 | Data validation framework | Next |
| 5-8 | Snowflake + dimensional warehouse + dbt marts | Future |
| 9 | Power BI | Future |
| 10-15 | Airflow, incremental, Docker, testing, CI/CD, monitoring | Future |

## Security

- All credentials live in `.env` (gitignored); `.env.example` holds placeholders only.
- S3 bucket blocks public access and uses server-side encryption.
- Cloud IAM follows the principle of least privilege.
