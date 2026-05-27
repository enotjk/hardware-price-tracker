-- =============================================
-- MIGRATION 04: exchange_rates
-- Курсы валют по дням
-- =============================================
CREATE TABLE exchange_rates (
    id            SERIAL PRIMARY KEY,
    date          DATE         NOT NULL,
    from_currency VARCHAR(5)   NOT NULL,  -- 'EUR', 'GBP'
    to_currency   VARCHAR(5)   NOT NULL,  -- всегда 'USD'
    rate          DECIMAL(10,6) NOT NULL,
    created_at    TIMESTAMPTZ  DEFAULT NOW(),
 
    UNIQUE(date, from_currency, to_currency)
);
 
CREATE INDEX idx_exchange_rates_date ON exchange_rates(date);
 