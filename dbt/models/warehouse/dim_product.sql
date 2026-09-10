WITH source AS (
    SELECT * FROM {{ source('spa_staging', 'spa_products') }}
)

SELECT
    MD5(id) AS product_key,
    id AS product_id,
    name AS product_name,
    category,
    price
FROM source
