--
-- FACT_COMPLETED_ITEMS
-- --------------------
-- Baris per line item yang sudah termasuk dalam sebuah transaksi.
-- `item_key` dapat NULL (misal Gift Card atau Membership yang tidak
-- mempunyai treatment/product ID).
-- Foreign key:
--   - transaction_key -> fact_transactions
--   - item_key        -> dim_treatment / dim_product (optional)
-- Kolom `booking_log_id` dipertahankan untuk traceability ke
-- `fact_treatment_activities` bila diperlukan.
--

SELECT
    MD5(ci.id)                     AS completed_item_key,

    -- foreign key ke fact_transactions
    MD5(ci.transaction_id)        AS transaction_key,

    -- foreign key ke dim_treatment atau dim_product (bisa NULL)
    MD5(ci.item_id)               AS item_key,

    TO_VARCHAR(DATE(ci.created_at), 'YYYYMMDD')::INT AS date_key,

    -- measures
    ci.price,

    -- attributes
    ci.item_name,
    ci.booking_log_id,
    ci.created_at                 AS completed_timestamp
FROM {{ source('spa_staging', 'completed_items') }} ci
