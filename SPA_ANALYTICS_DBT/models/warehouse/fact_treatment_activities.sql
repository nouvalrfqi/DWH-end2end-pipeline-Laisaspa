--
-- FACT_TREATMENT_ACTIVITIES
-- -------------------------
-- Menyimpan satu baris per appointment (treatment) yang telah dijadwalkan.
-- Hanya menyertakan baris dengan item_type = 'treatment'.
-- Foreign key:
--   - customer_key       -> dim_customer
--   - treatment_key      -> dim_treatment
--   - scheduled_date_key -> dim_date
-- Kolom guest_name diletakkan di sini (bukan di dimensi), sehingga
-- Power BI dapat men-display nama tamu bersamaan dengan detail treatment.
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
