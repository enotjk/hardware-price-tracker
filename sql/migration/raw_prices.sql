-- =============================================
-- MIGRATION 05: raw_prices
-- Сырые данные из API — никогда не удаляем
-- =============================================
CREATE TABLE raw_prices (
    id            UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id     INTEGER      REFERENCES dim_sources(source_id),
    product_query VARCHAR(255) NOT NULL,   -- поисковый запрос ('RTX 4090')
    raw_json      JSONB        NOT NULL,   -- ответ API как есть
    fetched_at    TIMESTAMPTZ  DEFAULT NOW(),
    etl_run_id    VARCHAR(50),            -- ID запуска Airflow DAG
    status        VARCHAR(20)  DEFAULT 'raw',  -- 'raw', 'processed', 'error'
 
    CONSTRAINT valid_status CHECK (status IN ('raw', 'processed', 'error'))
);
 
CREATE INDEX idx_raw_prices_source    ON raw_prices(source_id);
CREATE INDEX idx_raw_prices_fetched   ON raw_prices(fetched_at);
CREATE INDEX idx_raw_prices_status    ON raw_prices(status);