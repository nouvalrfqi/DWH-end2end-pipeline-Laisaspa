--
-- FACT_TREATMENT_ACTIVITIES
-- -------------------------
-- One row per scheduled treatment appointment.
-- Only rows with item_type = 'treatment' are included.
-- Foreign keys:
--   - customer_key       -> dim_customer
--   - treatment_key      -> dim_treatment
--   - scheduled_date_key -> dim_date
-- guest_name lives on the fact so Power BI can display it alongside
-- treatment details.
--

SELECT
    MD5(bl.id)                     AS activity_key,
    bl.id                          AS booking_id,

    -- foreign keys
    MD5(bg.customer_phone)         AS customer_key,
    MD5(bl.treatment_id)          AS treatment_key,
    TO_VARCHAR(DATE(bl.scheduled_date), 'YYYYMMDD')::INT AS scheduled_date_key,

    -- measures
    bl.price,
    bl.guest_name,

    -- attributes
    bl.status,
    bl.scheduled_date
FROM {{ source('spa_staging', 'booking_logs') }} bl
LEFT JOIN {{ source('spa_staging', 'booking_groups') }} bg
       ON bl.group_id = bg.id
WHERE bl.item_type = 'treatment'
