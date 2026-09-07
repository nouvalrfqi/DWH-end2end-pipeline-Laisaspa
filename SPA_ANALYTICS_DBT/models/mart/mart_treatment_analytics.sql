--
-- MART_TREATMENT_ANALYTICS
-- ------------------------
-- Performa tiap treatment berdasarkan booking activity.
-- Grain: 1 baris per treatment_key.
-- SOP: dim_treatment + fact_treatment_activities.
-- Status yang dikenal: completed, cancelled, booked, no_show.
--

WITH treatments AS (
    SELECT * FROM {{ ref('dim_treatment') }}
),
activities AS (
    SELECT * FROM {{ ref('fact_treatment_activities') }}
),
agg AS (
    SELECT
        treatment_key,
        COUNT(*)                                       AS total_bookings,
        COUNT_IF(status = 'completed')                 AS completed_bookings,
        COUNT_IF(status = 'cancelled')                 AS cancelled_bookings,
        COUNT_IF(status = 'booked')                    AS booked_bookings,
        COUNT_IF(status = 'no_show')                   AS no_show_bookings,
        SUM(price)                                     AS booking_revenue,
        SUM(CASE WHEN status = 'completed' THEN price ELSE 0 END) AS completed_revenue
    FROM activities
    GROUP BY treatment_key
)

SELECT
    t.treatment_key,
    t.treatment_id,
    t.treatment_name,
    t.category,
    t.price                                          AS list_price,
    t.duration,
    t.is_active,
    COALESCE(a.total_bookings, 0)                    AS total_bookings,
    COALESCE(a.completed_bookings, 0)                AS completed_bookings,
    COALESCE(a.cancelled_bookings, 0)                AS cancelled_bookings,
    COALESCE(a.booked_bookings, 0)                   AS booked_bookings,
    COALESCE(a.no_show_bookings, 0)                  AS no_show_bookings,
    COALESCE(a.booking_revenue, 0)                   AS booking_revenue,
    COALESCE(a.completed_revenue, 0)                 AS completed_revenue,
    a.cancelled_bookings / NULLIF(a.total_bookings, 0) AS cancellation_rate
FROM treatments t
LEFT JOIN agg a ON t.treatment_key = a.treatment_key