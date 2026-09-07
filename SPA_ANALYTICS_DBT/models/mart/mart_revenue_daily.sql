--
-- MART_REVENUE_DAILY
-- ------------------
-- Pendapatan harian berdasarkan sumber transaksi.
-- Grain: 1 baris per (transaction_date, source).
-- NFK: date_key -> dim_date.
-- Metrik: #transaksi, gross, diskon, netto, AOV.
--

WITH transactions AS (
    SELECT * FROM {{ ref('fact_transactions') }}
),
date_dim AS (
    SELECT * FROM {{ ref('dim_date') }}
)

SELECT
    f.date_key,
    d.full_date                                        AS transaction_date,
    f.source,
    COUNT(*)                                           AS transaction_count,
    SUM(f.gross_amount)                                AS gross_revenue,
    SUM(f.discount_amount)                             AS total_discount,
    SUM(f.net_amount)                                  AS net_revenue,
    SUM(f.net_amount) / NULLIF(COUNT(*), 0)            AS avg_order_value
FROM transactions f
LEFT JOIN date_dim d ON f.date_key = d.date_key
GROUP BY f.date_key, d.full_date, f.source