--
-- FACT_COMPLETED_ITEMS
-- --------------------
-- One row per line item included in a transaction.
-- `item_key` can be NULL (e.g. Gift Cards or Memberships have no
-- treatment/product ID).
-- Foreign keys:
--   - transaction_key -> fact_transactions
--   - item_key        -> dim_treatment / dim_product (optional)
-- `booking_log_id` is kept for traceability to
-- `fact_treatment_activities`.
--

SELECT
    MD5(ci.id)                     AS completed_item_key,

    -- foreign key -> fact_transactions
    MD5(ci.transaction_id)        AS transaction_key,

    -- foreign key -> dim_treatment / dim_product (nullable)
    MD5(ci.item_id)               AS item_key,

    TO_VARCHAR(DATE(ci.created_at), 'YYYYMMDD')::INT AS date_key,

    -- measures
    ci.price,

    -- attributes
    ci.item_name,
    ci.booking_log_id,
    ci.created_at                 AS completed_timestamp
FROM {{ source('spa_staging', 'completed_items') }} ci
