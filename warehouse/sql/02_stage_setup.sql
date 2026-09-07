-- =============================================================
-- 02_stage_setup.sql
-- CSV file format + external stage pointing at the S3 data lake.
-- Idempotent: safe to run repeatedly (PRD section 17).
--
-- AUTHENTICATION STRATEGY:
-- Uses direct AWS credentials (KEY_ID / SECRET_KEY) instead of
-- a storage integration + IAM role.
--
-- Why not storage integration?
--   Snowflake's internal IAM user could not AssumeRole into our
--   AWS account (sts:AssumeRole denied — confirmed as a
--   Snowflake-side issue after exhaustive AWS diagnostics).
--
-- The credentials are injected at runtime by loader.py from the
-- environment variables AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY.
-- Placeholders {AWS_KEY_ID} and {AWS_SECRET_KEY} are replaced
-- before execution — DO NOT run this file directly in a worksheet;
-- use `python -m warehouse.loader --setup` instead.
--
-- To run manually in Snowflake Worksheet, replace the placeholders
-- with actual values or use the SQL in the walkthrough document.
--
-- Stage URL points at the raw/ prefix so COPY later uses
-- FROM @spa_stage/<table>/ (no extra 'raw/' segment).
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
