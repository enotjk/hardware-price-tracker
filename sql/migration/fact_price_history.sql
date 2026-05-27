-- =============================================
-- MIGRATION 06: fact_price_history
-- Главная таблица — все цены по времени
-- =============================================
CREATE TABLE fact_price_history (
    id               UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id       UUID         REFERENCES dim_products(product_id),
    source_id        INTEGER      REFERENCES dim_sources(source_id),
    date_id          DATE         REFERENCES dim_date(date_id),
 
    -- Цены
    price_usd        DECIMAL(10,2) NOT NULL,     -- нормализованная цена в USD
    price_original   DECIMAL(10,2) NOT NULL,     -- оригинальная цена
    currency         VARCHAR(5)    NOT NULL,      -- оригинальная валюта
 
    -- Контекст
    exchange_rate    DECIMAL(10,6) DEFAULT 1.0,  -- курс на момент сбора
    in_stock         BOOLEAN       DEFAULT true,
    seller_name      VARCHAR(255),
    product_url      TEXT,
    listing_title    TEXT,                        -- название листинга из API
 
    -- ETL метаданные
    collected_at     TIMESTAMPTZ   DEFAULT NOW(),
    etl_run_id       VARCHAR(50),
    raw_price_id     UUID          REFERENCES raw_prices(id)
);
 
-- Индексы для быстрых запросов по времени и продукту
CREATE INDEX idx_fact_product_date  ON fact_price_history(product_id, collected_at);
CREATE INDEX idx_fact_source_date   ON fact_price_history(source_id, collected_at);
CREATE INDEX idx_fact_date_id       ON fact_price_history(date_id);