-- =============================================
-- MIGRATION 02: dim_products
-- Справочник товаров (GPU, CPU, RAM)
-- =============================================
CREATE TABLE dim_products (
    product_id    UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    name          VARCHAR(255) NOT NULL,         -- 'NVIDIA GeForce RTX 4090'
    brand         VARCHAR(50)  NOT NULL,         -- 'NVIDIA', 'AMD', 'Intel'
    category      VARCHAR(20)  NOT NULL,         -- 'GPU', 'CPU', 'RAM'
    model_number  VARCHAR(100),                  -- 'RTX 4090', 'RX 7900 XTX'
    msrp_usd     DECIMAL(10,2),                 -- официальная цена в USD
    tdp_watts     INTEGER,                       -- потребление (для GPU)
    vram_gb       INTEGER,                       -- видеопамять (для GPU)
    cores         INTEGER,                       -- ядра (для CPU)
    release_date  DATE,
    is_active     BOOLEAN      DEFAULT true,
    created_at    TIMESTAMPTZ  DEFAULT NOW(),
 
    CONSTRAINT valid_category CHECK (category IN ('GPU', 'CPU', 'RAM'))
);
 
CREATE INDEX idx_products_category ON dim_products(category);
CREATE INDEX idx_products_brand    ON dim_products(brand);