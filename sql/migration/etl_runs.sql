-- =============================================
-- MIGRATION 07: etl_runs
-- Лог запусков Airflow DAG — для ETL монитора
-- =============================================
CREATE TABLE etl_runs (
    id                UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    dag_id            VARCHAR(100) NOT NULL,   -- 'dag_ebay', 'dag_amazon'
    run_id            VARCHAR(100),            -- ID из Airflow
    status            VARCHAR(20)  NOT NULL,   -- 'running', 'success', 'failed'
    started_at        TIMESTAMPTZ  DEFAULT NOW(),
    finished_at       TIMESTAMPTZ,
    records_fetched   INTEGER      DEFAULT 0,
    records_inserted  INTEGER      DEFAULT 0,
    error_message     TEXT,
 
    CONSTRAINT valid_run_status CHECK (status IN ('running', 'success', 'failed'))
);
 
CREATE INDEX idx_etl_runs_dag    ON etl_runs(dag_id);
CREATE INDEX idx_etl_runs_status ON etl_runs(status);