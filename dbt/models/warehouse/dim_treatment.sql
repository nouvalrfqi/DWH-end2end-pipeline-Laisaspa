WITH source AS (
    SELECT * FROM {{ source('spa_staging', 'treatments') }}
),

renamed_and_hashed AS (
    SELECT
        MD5(id) AS treatment_key,
        id AS treatment_id,
        name AS treatment_name,
        category,
        price,
        duration,
        is_active
    FROM source
)

SELECT * FROM renamed_and_hashed
