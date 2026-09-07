WITH date_spine AS (
    SELECT DATEADD(day, SEQ4(), '2020-01-01') AS date_day
    FROM TABLE (GENERATOR(ROWCOUNT => 3650))
)
SELECT 
    TO_VARCHAR(date_day, 'YYYYMMDD')::INT AS date_key,
    date_day AS full_date,
    YEAR(date_day) AS year,
    MONTH(date_day) AS month,
    MONTHNAME(date_day) AS month_name,
    DAY(date_day) AS day,
    DAYNAME(date_day) AS day_of_week,
    QUARTER(date_day) AS quarter
FROM date_spine
