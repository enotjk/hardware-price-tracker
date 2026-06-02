"""
DAG: dag_amazon
Сбор цен с Amazon US и DE через RapidAPI каждые 12 часов.

  fetch_amazon_us ──┐
                    ├──► normalize_and_save ──► update_etl_log
  fetch_amazon_de ──┘
        │
  get_exchange_rate (параллельно)
"""

from __future__ import annotations

import sys
import logging
from datetime import datetime, timedelta, date

from airflow import DAG
from airflow.operators.python import PythonOperator

sys.path.insert(0, "/opt/airflow/extractors")
sys.path.insert(0, "/opt/airflow/transformers")
sys.path.insert(0, "/opt/airflow/db")

log = logging.getLogger(__name__)

SOURCE_IDS = {
    "amazon_us": 3,
    "amazon_de": 4,
}

default_args = {
    "owner": "hardware-tracker",
    "retries": 2,
    "retry_delay": timedelta(minutes=15),
    "email_on_failure": False,
    "email_on_retry": False,
}

with DAG(
    dag_id="dag_amazon",
    description="Сбор цен с Amazon US и DE каждые 12 часов",
    default_args=default_args,
    start_date=datetime(2024, 1, 1),
    schedule_interval="0 */12 * * *",
    catchup=False,
    max_active_runs=1,
    tags=["amazon", "prices"],
) as dag:

    def fetch_amazon_us(**context):
        from amazon import AmazonClient
        from connection import get_connection
        from writer import Writer

        run_id = context["run_id"]
        conn = get_connection()
        writer = Writer(conn)
        client = AmazonClient()

        all_listings = []

        for category in ["GPU", "CPU", "RAM"]:
            try:
                listings = client.search_category(category, region="US")
                if listings:
                    raw_data = [
                        {
                            "title": l.title, "price": l.price,
                            "currency": l.currency, "url": l.item_url,
                            "asin": l.item_id, "rating": l.rating,
                            "reviews": l.reviews_count,
                        }
                        for l in listings
                    ]
                    writer.save_raw(
                        SOURCE_IDS["amazon_us"],
                        f"amazon_us_{category.lower()}",
                        raw_data,
                        run_id,
                    )
                    all_listings.extend([(l, SOURCE_IDS["amazon_us"]) for l in listings])
                    conn.commit()
                    log.info(f"Amazon US {category}: {len(listings)} листингов")
            except Exception as e:
                log.error(f"Ошибка Amazon US {category}: {e}")
                conn.rollback()

        conn.close()

        # Передаём листинги И счётчик запросов
        serialized = [
            {
                "title": l.title, "price": l.price, "currency": l.currency,
                "region": l.region, "availability": l.availability,
                "seller_name": l.seller_name, "item_url": l.item_url,
                "source_id": sid,
            }
            for l, sid in all_listings
        ]
        ti = context["task_instance"]
        ti.xcom_push(key="amazon_us_listings", value=serialized)
        ti.xcom_push(key="api_requests_used", value=client.get_request_count())

        log.info(f"Amazon US: {len(serialized)} листингов, {client.get_request_count()} запросов API")
        return len(serialized)

    def fetch_amazon_de(**context):
        from amazon import AmazonClient
        from connection import get_connection
        from writer import Writer

        run_id = context["run_id"]
        conn = get_connection()
        writer = Writer(conn)
        client = AmazonClient()

        all_listings = []

        for category in ["GPU", "CPU", "RAM"]:
            try:
                listings = client.search_category(category, region="DE")
                if listings:
                    raw_data = [
                        {
                            "title": l.title, "price": l.price,
                            "currency": l.currency, "url": l.item_url,
                            "asin": l.item_id, "rating": l.rating,
                            "reviews": l.reviews_count,
                        }
                        for l in listings
                    ]
                    writer.save_raw(
                        SOURCE_IDS["amazon_de"],
                        f"amazon_de_{category.lower()}",
                        raw_data,
                        run_id,
                    )
                    all_listings.extend([(l, SOURCE_IDS["amazon_de"]) for l in listings])
                    conn.commit()
                    log.info(f"Amazon DE {category}: {len(listings)} листингов")
            except Exception as e:
                log.error(f"Ошибка Amazon DE {category}: {e}")
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
        ti = context["task_instance"]
        ti.xcom_push(key="amazon_de_listings", value=serialized)
        ti.xcom_push(key="api_requests_used", value=client.get_request_count())

        log.info(f"Amazon DE: {len(serialized)} листингов, {client.get_request_count()} запросов API")
        return len(serialized)

    def get_exchange_rate(**context):
        from exchange_rates import ExchangeRateClient
        from connection import get_connection

        client = ExchangeRateClient()
        eur_rate = client.get_rate("EUR", "USD")

        conn = get_connection()
        client.save_rates_to_db(conn)
        conn.commit()
        conn.close()

        rates = {"EUR": eur_rate}
        context["task_instance"].xcom_push(key="exchange_rates", value=rates)
        log.info(f"Курсы обновлены: {rates}")
        return rates

    def normalize_and_save(**context):
        from normalizer import Normalizer
        from deduplicator import Deduplicator
        from exchange_rates import ExchangeRateClient
        from connection import get_connection
        from writer import Writer
        from dataclasses import dataclass
        from typing import Optional
        from collections import defaultdict

        ti = context["task_instance"]
        run_id = context["run_id"]
        today = str(date.today())

        us_listings = ti.xcom_pull(task_ids="fetch_amazon_us", key="amazon_us_listings") or []
        de_listings = ti.xcom_pull(task_ids="fetch_amazon_de", key="amazon_de_listings") or []
        all_raw = us_listings + de_listings

        log.info(f"Получено листингов: US={len(us_listings)}, DE={len(de_listings)}")

        if not all_raw:
            log.warning("Нет данных для нормализации")
            ti.xcom_push(key="inserted_count", value=0)
            return 0

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
        by_source = defaultdict(list)
        for listing, source_id in listings_with_source:
            by_source[source_id].append(listing)

        for source_id, listings in by_source.items():
            normalized, skipped = normalizer.normalize_batch(
                listings, source_id=source_id,
                date_id=today, etl_run_id=run_id,
            )
            unique = deduplicator.deduplicate(normalized)
            unique = deduplicator.filter_existing(unique, conn)
            inserted, _ = writer.save_normalized(unique)
            conn.commit()
            total_inserted += inserted
            log.info(f"Source {source_id}: вставлено {inserted} записей")

        conn.close()
        ti.xcom_push(key="inserted_count", value=total_inserted)
        log.info(f"Всего вставлено: {total_inserted} записей")
        return total_inserted

    def update_etl_log(**context):
        from connection import get_connection
        from writer import Writer

        ti = context["task_instance"]
        run_id = context["run_id"]

        us_count = ti.xcom_pull(task_ids="fetch_amazon_us") or 0
        de_count = ti.xcom_pull(task_ids="fetch_amazon_de") or 0
        inserted = ti.xcom_pull(task_ids="normalize_and_save", key="inserted_count") or 0

        # Суммируем запросы с обоих тасков
        us_requests = ti.xcom_pull(task_ids="fetch_amazon_us", key="api_requests_used") or 0
        de_requests = ti.xcom_pull(task_ids="fetch_amazon_de", key="api_requests_used") or 0
        total_requests = us_requests + de_requests

        conn = get_connection()
        writer = Writer(conn)
        writer.log_etl_run(
            dag_id="dag_amazon",
            run_id=run_id,
            status="success",
            records_fetched=us_count + de_count,
            records_inserted=inserted,
            api_requests_used=total_requests,
        )
        conn.commit()
        conn.close()
        log.info(f"ETL лог: fetched={us_count + de_count}, inserted={inserted}, api_requests={total_requests}")

    t1_us   = PythonOperator(task_id="fetch_amazon_us",    python_callable=fetch_amazon_us)
    t2_de   = PythonOperator(task_id="fetch_amazon_de",    python_callable=fetch_amazon_de)
    t3_rate = PythonOperator(task_id="get_exchange_rate",  python_callable=get_exchange_rate)
    t4_norm = PythonOperator(task_id="normalize_and_save", python_callable=normalize_and_save)
    t5_log  = PythonOperator(task_id="update_etl_log",     python_callable=update_etl_log)

    [t1_us, t2_de, t3_rate] >> t4_norm >> t5_log