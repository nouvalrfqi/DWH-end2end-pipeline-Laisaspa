-- =============================================================
-- 02_storage_integration.sql
-- Bridge between AWS S3 (data lake) and Snowflake.
-- Idempotent: safe to run repeatedly (PRD section 17).
--
-- NOTE: STORAGE_AWS_ROLE_ARN is a PLACEHOLDER. The real flow:
--   1. Run this file once -> DESCRIBE STORAGE INTEGRATION -> Snowflake
--      returns its own AWS IAM user ARN + external ID.
--   2. In AWS Console create IAM role 'spa-snowflake-read' with a trust
--      policy allowing ONLY that Snowflake IAM user (external ID), plus a
--      read-only policy on s3://spa-data-platform-dev/raw/.
--   3. ALTER STORAGE INTEGRATION spa_s3_integration
--        SET STORAGE_AWS_ROLE_ARN = '<real-arn>';
--
-- Stage URL points at the raw/ prefix (decision: Option A), so COPY later
-- uses FROM @spa_stage/<table>/ (no extra 'raw/' segment).
-- =============================================================

CREATE FILE FORMAT IF NOT EXISTS SPA_ANALYTICS.STAGING.spa_csv_format
    TYPE = CSV
    SKIP_HEADER                   = 1
    FIELD_OPTIONALLY_ENCLOSED_BY  = '"'
    EMPTY_FIELD_AS_NULL           = TRUE
    NULL_IF                       = ('NULL', '')
    ERROR_ON_COLUMN_COUNT_MISMATCH = FALSE;

CREATE STORAGE INTEGRATION IF NOT EXISTS spa_s3_integration
    TYPE                    = EXTERNAL_STAGE
    STORAGE_PROVIDER        = 'S3'
    ENABLED                 = TRUE
    STORAGE_AWS_ROLE_ARN    = 'arn:aws:iam::000000000000:role/spa-snowflake-read'
    STORAGE_ALLOWED_LOCATIONS = ('s3://spa-data-platform-dev/raw/');

CREATE STAGE IF NOT EXISTS SPA_ANALYTICS.STAGING.spa_stage
    URL                 = 's3://spa-data-platform-dev/raw/'
    STORAGE_INTEGRATION = spa_s3_integration
    FILE_FORMAT         = (FORMAT_NAME = SPA_ANALYTICS.STAGING.spa_csv_format);
