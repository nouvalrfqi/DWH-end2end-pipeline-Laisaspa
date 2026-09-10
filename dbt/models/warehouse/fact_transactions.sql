WITH transactions AS (
    SELECT * FROM {{ source('spa_staging', 'transactions') }}
)

SELECT
    MD5(t.id) AS transaction_key,
    t.id AS transaction_id,
    MD5(t.customer_phone) AS customer_key,
    TO_VARCHAR(DATE(t.created_at), 'YYYYMMDD')::INT AS date_key,
    (t.total_price + t.discount_amount) AS gross_amount,
    t.discount_amount,
    t.total_price AS net_amount,
    t.source,
    t.created_at AS transaction_timestamp
FROM transactions t
