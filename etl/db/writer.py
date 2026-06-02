"""
Writer — сохранение данных в PostgreSQL (Supabase)
"""
from __future__ import annotations

import json
import logging
from typing import Optional
from psycopg2.extras import execute_values

log = logging.getLogger(__name__)


class Writer:
    def __init__(self, conn):
        self.conn = conn

    def save_raw(self, source_id, query, raw_data, etl_run_id=None):
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO raw_prices (source_id, product_query, raw_json, etl_run_id, status)
            VALUES (%s, %s, %s, %s, 'raw')
            RETURNING id
        """, (source_id, query, json.dumps(raw_data), etl_run_id))
        raw_id = str(cursor.fetchone()[0])
        cursor.close()
        log.info(f"raw_prices: сохранено {len(raw_data)} записей для '{query}'")
        return raw_id

    def save_normalized(self, records):
        if not records:
            return 0, 0

        cursor = self.conn.cursor()
        inserted_count = 0
        skipped_count = 0

        for r in records:
            try:
                cursor.execute("""
                    INSERT INTO fact_price_history (
                        product_id, source_id, date_id,
                        price_usd, price_original, currency, exchange_rate,
                        in_stock, seller_name, product_url, listing_title,
                        etl_run_id, raw_price_id
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    r.product_id, r.source_id, r.date_id,
                    r.price_usd, r.price_original, r.currency, r.exchange_rate,
                    r.in_stock, r.seller_name, r.product_url, r.listing_title,
                    r.etl_run_id, r.raw_price_id,
                ))
                inserted_count += 1
            except Exception as e:
                if "duplicate" in str(e).lower() or "unique" in str(e).lower():
                    skipped_count += 1
                    self.conn.rollback()
                else:
                    log.error(f"Ошибка вставки: {e}")
                    self.conn.rollback()

        cursor.close()
        log.info(f"fact_price_history: вставлено {inserted_count}, пропущено {skipped_count}")
        return inserted_count, skipped_count

    def log_etl_run(
        self,
        dag_id: str,
        status: str,
        records_fetched: int = 0,
        records_inserted: int = 0,
        error_message: Optional[str] = None,
        run_id: Optional[str] = None,
        api_requests_used: Optional[int] = None,   # ← новый параметр
    ) -> None:
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO etl_runs (
                dag_id, run_id, status,
                records_fetched, records_inserted,
                error_message, api_requests_used, finished_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
        """, (
            dag_id, run_id, status,
            records_fetched, records_inserted,
            error_message, api_requests_used,
        ))
        cursor.close()
        log.info(f"ETL лог: {dag_id} → {status} ({records_inserted} записей, {api_requests_used} API запросов)")