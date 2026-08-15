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
|-- warehouse/             # Snowflake loader + DDL scripts (Phase 5)
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
- Snowflake account (trial/enterprise) with a user that can run DDL

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

## Snowflake Staging (Phase 5)

Membawa data dari AWS S3 (data lake) ke Snowflake `STAGING` dengan pola ELT:
Python hanya men-trigger SQL + mencatat metadata, mesin **Snowflake** yang membaca S3 via `COPY INTO`.

```text
S3 s3://spa-data-platform-dev/raw/<table>/...
   |  SQL COPY INTO @spa_stage/<table>/
   v
SPA_ANALYTICS.STAGING.<table>   (11 tables)
```

### 1. Buat akun Snowflake (trial)

1. Daftar di <https://signup.snowflake.com> (trial 30 hari).
2. Ambil **account identifier** dari URL setelah login:
   `https://<orgname>-<accountname>.snowflakecomputing.com` → `SNOWFLAKE_ACCOUNT=<orgname>-<accountname>`.
3. Gunakan user + password dengan role berhak DDL (mis. `ACCOUNTADMIN` untuk tahap awal).

### 2. Isi `.env`

```bash
SNOWFLAKE_ACCOUNT=<orgname>-<accountname>   # contoh: XYCDJIV-IL38768
SNOWFLAKE_USERNAME=<your_snowflake_username>
SNOWFLAKE_PASSWORD=<your_snowflake_password>
SNOWFLAKE_ROLE=ACCOUNTADMIN
SNOWFLAKE_WAREHOUSE=SPA_WH
SNOWFLAKE_DATABASE=SPA_ANALYTICS
SNOWFLAKE_SCHEMA=STAGING
```

> `SPA_WH` / `SPA_ANALYTICS` / `STAGING` dibuat oleh `--setup`; mengisinya di `.env`
> aman dilakukan sebelum objek ada.

### 3. Verifikasi koneksi

> Pastikan `python` yang dipakai berasal dari venv project
> (`source .venv/bin/activate` dulu, atau `".venv/bin/python"` langsung).
> Python sistem (mis. Homebrew) tidak punya `snowflake-connector-python`.

```bash
python scripts/check_snowflake.py
# PASS snowflake: connected
#   account   = XS43148
#   user      = NOUVALRFQI
#   role      = ACCOUNTADMIN
#   warehouse = (none — expected before --setup)
```

### 4. Wire AWS IAM role (sekali saja, via AWS Console)

`--load` memakai storage integration ke S3 yang butuh IAM role (`spa-snowflake-read`).

1. Jalankan setup dulu untuk membuat objek dan mendapat nilai Snowflake-side:
   ```bash
   python -m warehouse.loader --setup
   ```
2. Ambil IAM user + external ID milik Snowflake:
   ```sql
   DESCRIBE STORAGE INTEGRATION spa_s3_integration;
   -- STORAGE_AWS_IAM_USER_ARN = arn:aws:iam::<sf-aws-account>:user/<...>
   -- STORAGE_AWS_EXTERNAL_ID   = <external-id>
   ```
3. Di AWS Console (region `ap-southeast-1`, bucket `spa-data-platform-dev`) buat
   IAM role **`spa-snowflake-read`** dengan **trust policy** yang hanya mengizinkan
   user Snowflake tersebut, lengkap dengan external ID:
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [{
       "Effect": "Allow",
       "Principal": { "AWS": "<STORAGE_AWS_IAM_USER_ARN>" },
       "Action": "sts:AssumeRole",
       "Condition": { "StringEquals": { "sts:ExternalId": "<STORAGE_AWS_EXTERNAL_ID>" } }
     }]
   }
   ```
4. Lampirkan **inline policy** read-only berikut ke role:
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [{
       "Effect": "Allow",
       "Action": ["s3:GetObject", "s3:GetBucketLocation"],
       "Resource": [
         "arn:aws:s3:::spa-data-platform-dev",
         "arn:aws:s3:::spa-data-platform-dev/raw/*"
       ]
     }]
   }
   ```
5. Arahkan storage integration ke role asli (mengganti ARN placeholder `000000000000`):
   ```sql
   ALTER STORAGE INTEGRATION spa_s3_integration
     SET STORAGE_AWS_ROLE_ARN = 'arn:aws:iam::<your-aws-account>:role/spa-snowflake-read';
   ```

### 5. Setup objek Snowflake (idempotent, aman dijalankan ulang)

```bash
python -m warehouse.loader --setup
# [setup] 01_database_warehouse.sql: 5 statement(s) executed
# [setup] 02_storage_integration.sql: 3 statement(s) executed
# [setup] 03_staging_tables.sql: 11 statement(s) executed
# [setup] STAGING tables found: 11
```

Yang dibuat: DB `SPA_ANALYTICS`, warehouse `SPA_WH` (XSMALL, auto-suspend 300s),
schemas `STAGING`/`WAREHOUSE`/`MART`, file format `SPA_CSV_FORMAT`, storage integration
`SPA_S3_INTEGRATION`, stage `SPA_STAGE`, dan 11 tabel staging (di-generate dari skema
Supabase asli — `python -m warehouse.ddl_generator`).

### 6. Load data (full load)

```bash
python -m warehouse.loader --load
```

Per tabel: `TRUNCATE` → `COPY INTO @spa_stage/<table>/ PATTERN='.*\.csv'` → `SELECT COUNT(*)`.
Metadata batch ditulis ke `logs/load_log_<batch>.json`. Opsi:

- `--tables transactions,members` → hanya tabel tertentu.
- `--batch-id <id>` → batch id custom.
- `error_policy: continue` di `config/tables.yaml` → satu tabel gagal tidak menghentikan tabel lain.

### 7. Verifikasi count sumber vs staging

Cek count sumber (Supabase) dengan `python main.py`, lalu bandingkan di Snowflake:

```sql
SELECT 'transactions' AS t, COUNT(*) FROM SPA_ANALYTICS.STAGING.transactions
UNION ALL SELECT 'booking_logs', COUNT(*) FROM SPA_ANALYTICS.STAGING.booking_logs;
```

Baseline awal: `transactions 179`, `booking_logs 279`, dst.

## Environment Variables

See [`.env.example`](./.env.example) for the full list. Keep all credentials in `.env`
and never commit secrets to Git.

## Roadmap / Status

| Phase | Scope | Status |
|---|---|---|
| 0 | Business & design (KPI, source mapping, star schema) | Done |
| 1-2 | Cloud infra + connectivity | Done |
| 3 | Generic extraction framework | Done |
| 4 | Data validation framework | Done |
| 5 | Snowflake: DDL, loader, setup, staging load | In progress (setup done; `--load` menunggu wiring IAM role) |
| 6-8 | Snowflake dimensional warehouse + dbt marts | Future |
| 9 | Power BI | Future |
| 10-15 | Airflow, incremental, Docker, testing, CI/CD, monitoring | Future |

## Security

- All credentials live in `.env` (gitignored); `.env.example` holds placeholders only.
- S3 bucket blocks public access and uses server-side encryption.
- Cloud IAM follows the principle of least privilege.
