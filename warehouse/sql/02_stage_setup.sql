-- =============================================================
-- 02_stage_setup.sql
-- CSV file format + external stage pointing at the S3 data lake.
-- Idempotent: safe to run repeatedly.
--
-- AUTHENTICATION:
-- Uses direct AWS credentials injected by loader.py from the
-- environment (AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY). A storage
-- integration + IAM role was considered but blocked by an
-- sts:AssumeRole restriction between Snowflake and this AWS account.
-- Placeholders {AWS_KEY_ID} / {AWS_SECRET_KEY} are replaced before
-- execution; run via `python -m warehouse.loader --setup`.
--
-- Stage URL points at the raw/ prefix so COPY uses @spa_stage/<table>/.
-- =============================================================

CREATE FILE FORMAT IF NOT EXISTS SPA_ANALYTICS.STAGING.spa_csv_format
    TYPE = CSV
    SKIP_HEADER                   = 1
    FIELD_OPTIONALLY_ENCLOSED_BY  = '"'
    EMPTY_FIELD_AS_NULL           = TRUE
    NULL_IF                       = ('NULL', '')
    ERROR_ON_COLUMN_COUNT_MISMATCH = FALSE;

CREATE OR REPLACE STAGE SPA_ANALYTICS.STAGING.spa_stage
    URL = 's3://spa-data-platform-dev/raw/'
    CREDENTIALS = (
        AWS_KEY_ID     = '{AWS_KEY_ID}'
        AWS_SECRET_KEY = '{AWS_SECRET_KEY}'
    )
    FILE_FORMAT = (FORMAT_NAME = SPA_ANALYTICS.STAGING.spa_csv_format);