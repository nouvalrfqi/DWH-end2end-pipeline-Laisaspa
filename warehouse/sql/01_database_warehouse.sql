-- =============================================================
-- 01_database_warehouse.sql
-- Foundation objects: database, warehouse (compute), schemas.
-- Idempotent: safe to run repeatedly (PRD section 17).
-- DDL only -> can run without an active warehouse (bootstrap mode).
-- =============================================================

CREATE DATABASE IF NOT EXISTS SPA_ANALYTICS;

CREATE WAREHOUSE IF NOT EXISTS SPA_WH
    WITH WAREHOUSE_SIZE = 'XSMALL'
         AUTO_SUSPEND   = 300
         AUTO_RESUME    = TRUE;

CREATE SCHEMA IF NOT EXISTS SPA_ANALYTICS.STAGING;
CREATE SCHEMA IF NOT EXISTS SPA_ANALYTICS.WAREHOUSE;
CREATE SCHEMA IF NOT EXISTS SPA_ANALYTICS.MART;
