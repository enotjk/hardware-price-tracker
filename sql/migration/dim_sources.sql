-- =============================================
-- MIGRATION 01: dim_sources
-- Справочник источников данных (магазины)
-- =============================================
CREATE TABLE dim_sources (
    source_id     SERIAL PRIMARY KEY,
    name          VARCHAR(50)  NOT NULL,  -- 'amazon', 'ebay', 'newegg'
    display_name  VARCHAR(100) NOT NULL,  -- 'Amazon US', 'eBay Germany'
    region        VARCHAR(10)  NOT NULL,  -- 'US', 'DE', 'UK'
    currency      VARCHAR(5)   NOT NULL,  -- 'USD', 'EUR', 'GBP'
    base_url      VARCHAR(255) NOT NULL,
    is_active     BOOLEAN      DEFAULT true,
    created_at    TIMESTAMPTZ  DEFAULT NOW()
);
 
-- Заполняем сразу — эти данные не меняются
INSERT INTO dim_sources (name, display_name, region, currency, base_url) VALUES
    ('ebay',    'eBay US',      'US', 'USD', 'https://www.ebay.com'),
    ('ebay',    'eBay Germany', 'DE', 'EUR', 'https://www.ebay.de'),
    ('amazon',  'Amazon US',    'US', 'USD', 'https://www.amazon.com'),
    ('amazon',  'Amazon DE',    'DE', 'EUR', 'https://www.amazon.de'),
    ('newegg',  'Newegg US',    'US', 'USD', 'https://www.newegg.com');