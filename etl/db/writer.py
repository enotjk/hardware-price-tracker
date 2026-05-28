"""
Writer — сохранение данных в PostgreSQL (Supabase)
Отвечает за запись в две таблицы:
  - raw_prices: сырые JSON данные из API (никогда не удаляем)
  - fact_price_history: нормализованные цены для аналитики
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Optional
from psycopg2.extras import execute_values

log = logging.getLogger(__name__)


class Writer:
    """
    Записывает данные в БД.

    Использование:
        conn = get_connection()
        writer = Writer(conn)
        raw_id = writer.save_raw(source_id=1, query="RTX 4090", raw_data=[...])
        writer.save_normalized(records)
        conn.commit()
        conn.close()
    """

    def __init__(self, conn):
        self.conn = conn

    # ─────────────────────────────────────
    # Сохранение сырых данных
    # ─────────────────────────────────────
    def save_raw(
        self,
        source_id: int,
        query: str,
        raw_data: list,
        etl_run_id: Optional[str] = None,
    ) -> str:
        """
        Сохраняет сырой ответ API в таблицу raw_prices.
        Всегда сохраняем — даже если данные потом не пройдут нормализацию.
        Это позволяет перепарсить их позже если изменится логика.

        Args:
            source_id:  ID источника из dim_sources (1=eBay US, 2=eBay DE и т.д.)
            query:      поисковый запрос ('RTX 4090')
            raw_data:   список объектов из API (list of dicts)
            etl_run_id: ID запуска (для трассировки)

        Returns:
            UUID вставленной записи
        """
        cursor = self.conn.cursor()

        cursor.execute("""
            INSERT INTO raw_prices (source_id, product_query, raw_json, etl_run_id, status)
            VALUES (%s, %s, %s, %s, 'raw')
            RETURNING id
        """, (
            source_id,
            query,
            json.dumps(raw_data),
            etl_run_id,
        ))

        raw_id = str(cursor.fetchone()[0])
        cursor.close()

        log.info(f"raw_prices: сохранено {len(raw_data)} записей для '{query}' (id={raw_id[:8]}...)")
        return raw_id

    # ─────────────────────────────────────
    # Сохранение нормализованных данных
    # ─────────────────────────────────────
    def save_normalized(self, records: list) -> tuple[int, int]:
        """
        Батч-вставка нормализованных записей в fact_price_history.
        Пропускает дубли (один продукт + источник за один день).

        Args:
            records: список NormalizedPrice из normalizer.py

        Returns:
            (inserted, skipped) — сколько вставлено и пропущено
        """
        if not records:
            log.info("Нет записей для вставки")
            return 0, 0

        cursor = self.conn.cursor()

        # Подготавливаем данные для батч-вставки
        values = []
        for r in records:
            values.append((
                r.product_id,
                r.source_id,
                r.date_id,
                r.price_usd,
                r.price_original,
                r.currency,
                r.exchange_rate,
                r.in_stock,
                r.seller_name,
                r.product_url,
                r.listing_title,
                r.etl_run_id,
                r.raw_price_id,
            ))

        # INSERT с пропуском дублей
        # ON CONFLICT — если такой product_id + source_id + date уже есть,
        # обновляем цену (берём более актуальную)
        inserted_count = 0
        skipped_count = 0

        for value in values:
            try:
                cursor.execute("""
                    INSERT INTO fact_price_history (
                        product_id, source_id, date_id,
                        price_usd, price_original, currency, exchange_rate,
                        in_stock, seller_name, product_url, listing_title,
                        etl_run_id, raw_price_id
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                """, value)
                inserted_count += 1
            except Exception as e:
                if "duplicate" in str(e).lower() or "unique" in str(e).lower():
                    skipped_count += 1
                    self.conn.rollback()
                else:
                    log.error(f"Ошибка вставки записи: {e}")
                    self.conn.rollback()

        cursor.close()
        log.info(f"fact_price_history: вставлено {inserted_count}, пропущено {skipped_count} дублей")
        return inserted_count, skipped_count

    # ─────────────────────────────────────
    # Логирование ETL запуска
    # ─────────────────────────────────────
    def log_etl_run(
        self,
        dag_id: str,
        status: str,
        records_fetched: int = 0,
        records_inserted: int = 0,
        error_message: Optional[str] = None,
        run_id: Optional[str] = None,
    ) -> None:
        """
        Записывает результат ETL запуска в таблицу etl_runs.
        Эти данные показываются на странице ETL монитора.
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO etl_runs (dag_id, run_id, status, records_fetched, records_inserted, error_message, finished_at)
            VALUES (%s, %s, %s, %s, %s, %s, NOW())
        """, (dag_id, run_id, status, records_fetched, records_inserted, error_message))
        cursor.close()
        log.info(f"ETL лог: {dag_id} → {status} ({records_inserted} записей)")