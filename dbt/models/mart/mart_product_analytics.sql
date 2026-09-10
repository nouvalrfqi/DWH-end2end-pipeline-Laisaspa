--
-- MART_PRODUCT_ANALYTICS
-- ----------------------
-- Retail product sales.
-- Grain: 1 row per product_key.
-- Source: dim_product + fact_completed_items
--       (item_key matches product_key).
--

WITH products AS (
    SELECT * FROM {{ ref('dim_product') }}
),
completed_items AS (
    SELECT * FROM {{ ref('fact_completed_items') }}
),
sales AS (
    SELECT
        item_key                                    AS product_key,
        COUNT(*)                                    AS units_sold,
        SUM(price)                                  AS item_revenue
    FROM completed_items
    WHERE item_key IS NOT NULL
    GROUP BY item_key
)

SELECT
    p.product_key,
    p.product_id,
    p.product_name,
    p.category,
    p.price,
    COALESCE(s.units_sold, 0)                       AS units_sold,
    COALESCE(s.item_revenue, 0)                     AS item_revenue
FROM products p
LEFT JOIN sales s ON p.product_key = s.product_key