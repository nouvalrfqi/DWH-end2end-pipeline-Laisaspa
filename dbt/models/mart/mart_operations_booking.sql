--
-- MART_OPERATIONS_BOOKING
-- -----------------------
-- Booking volume by day, source page and status.
-- Grain: 1 row per (scheduled_date, source_page, status).
-- Source: fact_treatment_activities + source_page from booking_logs.
--

WITH activities AS (
    SELECT * FROM {{ ref('fact_treatment_activities') }}
),
booking_source AS (
    SELECT id, source_page
    FROM {{ source('spa_staging', 'booking_logs') }}
),
date_dim AS (
    SELECT * FROM {{ ref('dim_date') }}
)

SELECT
    f.scheduled_date_key,
    d.full_date                                      AS scheduled_date,
    COALESCE(bs.source_page, 'unknown')              AS source_page,
    f.status,
    COUNT(*)                                         AS booking_count,
    SUM(f.price)                                     AS booking_revenue
FROM activities f
LEFT JOIN booking_source bs ON f.booking_id = bs.id
LEFT JOIN date_dim d ON f.scheduled_date_key = d.date_key
GROUP BY f.scheduled_date_key, d.full_date, COALESCE(bs.source_page, 'unknown'), f.status