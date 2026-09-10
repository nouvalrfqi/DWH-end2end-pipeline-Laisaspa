--
-- MART_CUSTOMER_ANALYTICS
-- -----------------------
-- Customer profile and lifetime value.
-- Grain: 1 row per customer_key.
-- Source: dim_customer + aggregated fact_transactions.
--

WITH customers AS (
    SELECT * FROM {{ ref('dim_customer') }}
),
transactions AS (
    SELECT * FROM {{ ref('fact_transactions') }}
),
customer_agg AS (
    SELECT
        customer_key,
        COUNT(*)                                       AS transaction_count,
        SUM(gross_amount)                              AS total_gross,
        SUM(discount_amount)                           AS total_discount,
        SUM(net_amount)                                AS total_net,
        MIN(transaction_timestamp)                     AS first_transaction_at,
        MAX(transaction_timestamp)                     AS last_transaction_at
    FROM transactions
    GROUP BY customer_key
)

SELECT
    c.customer_key,
    c.customer_phone,
    c.customer_name,
    c.email,
    c.is_member,
    c.member_joined_date,
    c.total_visits,
    COALESCE(a.transaction_count, 0)                   AS transaction_count,
    COALESCE(a.total_gross, 0)                         AS total_gross,
    COALESCE(a.total_discount, 0)                      AS total_discount,
    COALESCE(a.total_net, 0)                           AS total_net,
    a.total_net / NULLIF(a.transaction_count, 0)       AS avg_transaction_value,
    a.first_transaction_at,
    a.last_transaction_at,
    DATEDIFF('day', a.last_transaction_at, CURRENT_TIMESTAMP) AS days_since_last_transaction
FROM customers c
LEFT JOIN customer_agg a ON c.customer_key = a.customer_key