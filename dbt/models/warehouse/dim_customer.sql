WITH booking_groups AS (
    SELECT customer_phone, customer_name, email, created_at
    FROM {{ source('spa_staging', 'booking_groups') }}
),

transactions AS (
    SELECT customer_phone, customer_name, NULL AS email, created_at
    FROM {{ source('spa_staging', 'transactions') }}
),

members AS (
    SELECT * FROM {{ source('spa_staging', 'members') }}
),

unique_customers AS (
    SELECT customer_phone, customer_name, email, created_at 
    FROM booking_groups
    
    UNION ALL
    
    SELECT customer_phone, customer_name, email, created_at 
    FROM transactions
),

deduped_customers AS (
    SELECT customer_phone, customer_name, email 
    FROM unique_customers 
    WHERE customer_phone IS NOT NULL
    QUALIFY ROW_NUMBER() OVER (
        PARTITION BY customer_phone
        ORDER BY created_at DESC 
    ) = 1
)

SELECT
    MD5(c.customer_phone) AS customer_key,
    c.customer_phone,
    c.customer_name,
    c.email,
    CASE
        WHEN m.id IS NOT NULL THEN TRUE
        ELSE FALSE
    END AS is_member,
    m.joined_date AS member_joined_date,
    m.total_visits
FROM deduped_customers c
LEFT JOIN members m ON c.customer_phone = m.phone
