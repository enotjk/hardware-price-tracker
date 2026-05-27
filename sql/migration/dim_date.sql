-- =============================================
-- MIGRATION 03: dim_date
-- Календарная таблица для аналитики
-- =============================================
CREATE TABLE dim_date (
    date_id       DATE PRIMARY KEY,
    year          INTEGER NOT NULL,
    quarter       INTEGER NOT NULL,
    month         INTEGER NOT NULL,
    month_name    VARCHAR(20) NOT NULL,
    week          INTEGER NOT NULL,
    day_of_month  INTEGER NOT NULL,
    day_of_week   INTEGER NOT NULL,  -- 1=Monday, 7=Sunday
    day_name      VARCHAR(20) NOT NULL,
    is_weekend    BOOLEAN NOT NULL
);
 
-- Заполняем на 3 года вперёд
INSERT INTO dim_date
SELECT
    d::DATE                                          AS date_id,
    EXTRACT(YEAR    FROM d)::INTEGER                 AS year,
    EXTRACT(QUARTER FROM d)::INTEGER                 AS quarter,
    EXTRACT(MONTH   FROM d)::INTEGER                 AS month,
    TO_CHAR(d, 'Month')                              AS month_name,
    EXTRACT(WEEK    FROM d)::INTEGER                 AS week,
    EXTRACT(DAY     FROM d)::INTEGER                 AS day_of_month,
    EXTRACT(ISODOW  FROM d)::INTEGER                 AS day_of_week,
    TO_CHAR(d, 'Day')                                AS day_name,
    EXTRACT(ISODOW  FROM d) IN (6, 7)                AS is_weekend
FROM generate_series('2024-01-01'::DATE, '2027-12-31'::DATE, '1 day') AS d;
 