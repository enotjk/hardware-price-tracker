"""
DAG: dag_ebay
Автоматический сбор цен с eBay US и DE каждые 6 часов.

Цепочка задач:
  fetch_ebay_us ──┐
                  ├──► normalize_and_save ──► update_etl_log
  fetch_ebay_de ──┘
        │
  get_exchange_rate (параллельно с fetch)

Данные сохраняются в:
  - raw_prices: сырые ответы API
  - fact_price_history: нормализованные цены в USD
  - etl_runs: лог запуска
"""

from __future__ import annotations

import sys
import os
import logging
from datetime import datetime, timedelta, date

from airflow import DAG
from airflow.operators.python import PythonOperator


# Добавляем наши модули в путь
sys.path.insert(0, "/opt/airflow/extractors")
sys.path.insert(0, "/opt/airflow/transformers")
sys.path.insert(0, "/opt/airflow/db")

log = logging.getLogger(__name__)

# ─────────────────────────────────────────
# Продукты для поиска
# ─────────────────────────────────────────
GPU_QUERIES = [
    "RTX 4090", "RTX 4080 Super", "RTX 4080",
    "RTX 4070 Ti Super", "RTX 4070 Super", "RTX 4070",
    "RTX 4060 Ti", "RTX 4060",
    "RX 7900 XTX", "RX 7900 XT", "RX 7800 XT", "RX 7600",
]
CPU_QUERIES = [
    "Core i9-14900K", "Core i7-14700K", "Core i5-14600K",
    "Ryzen 9 7950X", "Ryzen 7 7800X3D", "Ryzen 5 7600X",
]
RAM_QUERIES = [
    "DDR5-6000 32GB", "DDR5-5600 32GB", "DDR4-3600 32GB",
]

SOURCE_IDS = {
    "ebay_us": 1,
    "ebay_de": 2,
}

# ─────────────────────────────────────────
# Настройки DAG
# ─────────────────────────────────────────
default_args = {
    "owner": "hardware-tracker",
    "retries": 2,
    "retry_delay": timedelta(minutes=10),
    "email_on_failure": False,
    "email_on_retry": False,
}

with DAG(
    dag_id="dag_ebay",
    description="Сбор цен с eBay US и DE каждые 6 часов",
    default_args=default_args,
    start_date=datetime(2024, 1, 1),
    schedule_interval="0 */6 * * *",    # каждые 6 часов: 0:00, 6:00, 12:00, 18:00
    catchup=False,                       # не запускать пропущенные периоды
    max_active_runs=1,                   # только один запуск одновременно
    tags=["ebay", "prices"],
) as dag:

    # ─────────────────────────────────────
    # Task 1: Сбор данных с eBay US
    # ─────────────────────────────────────
    def fetch_ebay_us(**context):
        from ebay import EbayClient
        from connection import get_connection
        from writer import Writer

        run_id = context["run_id"]
        today = str(date.today())
        conn = get_connection()
        writer = Writer(conn)
        client = EbayClient()

        all_listings = []
        queries_map = {"GPU": GPU_QUERIES, "CPU": CPU_QUERIES, "RAM": RAM_QUERIES}

        for category, queries in queries_map.items():
            for query in queries:
                try:
                    listings = client.search(query, category=category, region="US", limit=10)
                    if listings:
                        raw_data = [
                            {"title": l.title, "price": l.price,
                             "currency": l.currency, "url": l.item_url}
                            for l in listings
                        ]
                        writer.save_raw(SOURCE_IDS["ebay_us"], query, raw_data, run_id)
                        all_listings.extend([(l, SOURCE_IDS["ebay_us"]) for l in listings])
                        conn.commit()
                        log.info(f"eBay US '{query}': {len(listings)} листингов")
                except Exception as e:
                    log.error(f"Ошибка eBay US '{query}': {e}")
                    conn.rollback()

        conn.close()

        # Передаём данные в следующую задачу через XCom
        serialized = [
            {
                "title": l.title, "price": l.price, "currency": l.currency,
                "region": l.region, "availability": l.availability,
                "seller_name": l.seller_name, "item_url": l.item_url,
                "source_id": sid,
            }
            for l, sid in all_listings
        ]
        context["task_instance"].xcom_push(key="ebay_us_listings", value=serialized)
        log.info(f"eBay US: всего собрано {len(serialized)} листингов")
        return len(serialized)

    # ─────────────────────────────────────
    # Task 2: Сбор данных с eBay DE
    # ─────────────────────────────────────
    def fetch_ebay_de(**context):
        from ebay import EbayClient
        from connection import get_connection
        from writer import Writer

        run_id = context["run_id"]
        conn = get_connection()
        writer = Writer(conn)
        client = EbayClient()

        all_listings = []
        queries_map = {"GPU": GPU_QUERIES, "CPU": CPU_QUERIES, "RAM": RAM_QUERIES}

        for category, queries in queries_map.items():
            for query in queries:
                try:
                    listings = client.search(query, category=category, region="DE", limit=10)
                    if listings:
                        raw_data = [
                            {"title": l.title, "price": l.price,
                             "currency": l.currency, "url": l.item_url}
                            for l in listings
                        ]
                        writer.save_raw(SOURCE_IDS["ebay_de"], query, raw_data, run_id)
                        all_listings.extend([(l, SOURCE_IDS["ebay_de"]) for l in listings])
                        conn.commit()
                        log.info(f"eBay DE '{query}': {len(listings)} листингов")
                except Exception as e:
                    log.error(f"Ошибка eBay DE '{query}': {e}")
                    conn.rollback()

        conn.close()

        serialized = [
            {
                "title": l.title, "price": l.price, "currency": l.currency,
                "region": l.region, "availability": l.availability,
                "seller_name": l.seller_name, "item_url": l.item_url,
                "source_id": sid,
            }
            for l, sid in all_listings
        ]
        context["task_instance"].xcom_push(key="ebay_de_listings", value=serialized)
        log.info(f"eBay DE: всего собрано {len(serialized)} листингов")
        return len(serialized)

    # ─────────────────────────────────────
    # Task 3: Получить курс валют
    # ─────────────────────────────────────
    def get_exchange_rate(**context):
        from exchange_rates import ExchangeRateClient
        from connection import get_connection

        client = ExchangeRateClient()
        eur_rate = client.get_rate("EUR", "USD")
        gbp_rate = client.get_rate("GBP", "USD")

        # Сохраняем в БД
        conn = get_connection()
        client.save_rates_to_db(conn)
        conn.commit()
        conn.close()

        rates = {"EUR": eur_rate, "GBP": gbp_rate}
        context["task_instance"].xcom_push(key="exchange_rates", value=rates)
        log.info(f"Курсы обновлены: {rates}")
        return rates

    # ─────────────────────────────────────
    # Task 4: Нормализация и сохранение
    # ─────────────────────────────────────
    def normalize_and_save(**context):
        from normalizer import Normalizer
        from deduplicator import Deduplicator
        from exchange_rates import ExchangeRateClient
        from connection import get_connection
        from writer import Writer
        from dataclasses import dataclass
        from typing import Optional

        ti = context["task_instance"]
        run_id = context["run_id"]
        today = str(date.today())

        # Получаем данные из предыдущих задач через XCom
        us_listings = ti.xcom_pull(task_ids="fetch_ebay_us", key="ebay_us_listings") or []
        de_listings = ti.xcom_pull(task_ids="fetch_ebay_de", key="ebay_de_listings") or []
        all_raw = us_listings + de_listings

        log.info(f"Получено листингов: US={len(us_listings)}, DE={len(de_listings)}")

        if not all_raw:
            log.warning("Нет данных для нормализации")
            context["task_instance"].xcom_push(key="inserted_count", value=0)
            return 0

        # Восстанавливаем объекты листингов из словарей
        @dataclass
        class SimpleListing:
            title: str
            price: float
            currency: str
            region: str
            availability: str
            seller_name: Optional[str]
            item_url: Optional[str]

        listings_with_source = [
            (SimpleListing(
                title=r["title"], price=r["price"], currency=r["currency"],
                region=r["region"], availability=r["availability"],
                seller_name=r["seller_name"], item_url=r["item_url"],
            ), r["source_id"])
            for r in all_raw
        ]

        # Загружаем продукты из БД
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT product_id, name, model_number, brand, category
            FROM dim_products WHERE is_active = true
        """)
        cols = [d[0] for d in cursor.description]
        products = [dict(zip(cols, row)) for row in cursor.fetchall()]
        cursor.close()

        exchange = ExchangeRateClient()
        normalizer = Normalizer(products, exchange)
        deduplicator = Deduplicator()
        writer = Writer(conn)

        total_inserted = 0

        # Группируем по source_id и нормализуем
        from collections import defaultdict
        by_source = defaultdict(list)
        for listing, source_id in listings_with_source:
            by_source[source_id].append(listing)

        for source_id, listings in by_source.items():
            normalized, skipped = normalizer.normalize_batch(
                listings, source_id=source_id,
                date_id=today, etl_run_id=run_id
            )
            unique = deduplicator.deduplicate(normalized)
            unique = deduplicator.filter_existing(unique, conn)
            inserted, _ = writer.save_normalized(unique)
            conn.commit()
            total_inserted += inserted
            log.info(f"Source {source_id}: вставлено {inserted} записей")

        conn.close()
        context["task_instance"].xcom_push(key="inserted_count", value=total_inserted)
        log.info(f"Всего вставлено: {total_inserted} записей")
        return total_inserted

    # ─────────────────────────────────────
    # Task 5: Лог результата в etl_runs
    # ─────────────────────────────────────
    def update_etl_log(**context):
        from connection import get_connection
        from writer import Writer

        ti = context["task_instance"]
        run_id = context["run_id"]

        us_count = ti.xcom_pull(task_ids="fetch_ebay_us") or 0
        de_count = ti.xcom_pull(task_ids="fetch_ebay_de") or 0
        inserted = ti.xcom_pull(task_ids="normalize_and_save", key="inserted_count") or 0

        conn = get_connection()
        writer = Writer(conn)
        writer.log_etl_run(
            dag_id="dag_ebay",
            run_id=run_id,
            status="success",
            records_fetched=us_count + de_count,
            records_inserted=inserted,
        )
        conn.commit()
        conn.close()
        log.info(f"ETL лог записан: fetched={us_count + de_count}, inserted={inserted}")

    # ─────────────────────────────────────
    # Создаём задачи
    # ─────────────────────────────────────
    t1_us = PythonOperator(
        task_id="fetch_ebay_us",
        python_callable=fetch_ebay_us,
    )

    t2_de = PythonOperator(
        task_id="fetch_ebay_de",
        python_callable=fetch_ebay_de,
    )

    t3_rate = PythonOperator(
        task_id="get_exchange_rate",
        python_callable=get_exchange_rate,
    )

    t4_norm = PythonOperator(
        task_id="normalize_and_save",
        python_callable=normalize_and_save,
    )

    t5_log = PythonOperator(
        task_id="update_etl_log",
        python_callable=update_etl_log,
    )

    # ─────────────────────────────────────
    # Зависимости задач:
    #
    # fetch_ebay_us ──┐
    #                 ├──► normalize_and_save ──► update_etl_log
    # fetch_ebay_de ──┘
    # get_exchange_rate ─┘
    # ─────────────────────────────────────
    [t1_us, t2_de, t3_rate] >> t4_norm >> t5_log