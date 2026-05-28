"""
run_collector.py — ручной запуск сбора данных
Запускай каждый день пока не настроен Airflow:

    python run_collector.py              # собрать всё
    python run_collector.py --source ebay    # только eBay
    python run_collector.py --source amazon  # только Amazon

Данные сохраняются в Supabase — строится историческая база.
"""

import os
import sys
import logging
import argparse
from datetime import date, datetime
from dotenv import load_dotenv

load_dotenv()

# Добавляем пути к нашим модулям
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "extractors"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "transformers"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "db"))

from ebay import EbayClient
from amazon import AmazonClient
from exchange_rates import ExchangeRateClient
from normalizer import Normalizer
from deduplicator import Deduplicator
from connection import get_connection
from writer import Writer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ─────────────────────────────────────────
# ID источников из таблицы dim_sources
# Должны совпадать с тем что вставили в INFRA-04
# ─────────────────────────────────────────
SOURCE_IDS = {
    "ebay_us": 1,
    "ebay_de": 2,
    "amazon_us": 3,
    "amazon_de": 4,
}

# Продукты для поиска — модели из dim_products
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


def load_products(conn) -> list[dict]:
    """Загружает список продуктов из dim_products"""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT product_id, name, model_number, brand, category
        FROM dim_products
        WHERE is_active = true
    """)
    cols = [d[0] for d in cursor.description]
    products = [dict(zip(cols, row)) for row in cursor.fetchall()]
    cursor.close()
    log.info(f"Загружено {len(products)} продуктов из dim_products")
    return products


def collect_ebay(conn, writer, normalizer, deduplicator, run_id: str):
    """Сбор данных с eBay US и DE"""
    log.info("=" * 50)
    log.info("Начинаем сбор данных с eBay...")
    log.info("=" * 50)

    client = EbayClient()
    today = str(date.today())
    total_inserted = 0

    queries_by_category = {
        "GPU": GPU_QUERIES,
        "CPU": CPU_QUERIES,
        "RAM": RAM_QUERIES,
    }

    for region, source_key in [("US", "ebay_us"), ("DE", "ebay_de")]:
        source_id = SOURCE_IDS[source_key]

        for category, queries in queries_by_category.items():
            for query in queries:
                try:
                    # 1. Получаем данные
                    listings = client.search(query, category=category, region=region, limit=10)

                    if not listings:
                        continue

                    # 2. Сохраняем сырые данные
                    raw_data = [
                        {"title": l.title, "price": l.price, "currency": l.currency,
                         "url": l.item_url, "seller": l.seller_name}
                        for l in listings
                    ]
                    raw_id = writer.save_raw(source_id, query, raw_data, run_id)

                    # 3. Нормализуем
                    normalized, skipped = normalizer.normalize_batch(
                        listings, source_id=source_id,
                        date_id=today, etl_run_id=run_id
                    )

                    # 4. Дедупликация
                    unique = deduplicator.deduplicate(normalized)
                    unique = deduplicator.filter_existing(unique, conn)

                    # 5. Сохраняем в fact_price_history
                    inserted, dup = writer.save_normalized(unique)
                    conn.commit()
                    total_inserted += inserted

                except Exception as e:
                    log.error(f"Ошибка при сборе eBay {region} '{query}': {e}")
                    conn.rollback()

    log.info(f"eBay завершён. Всего вставлено: {total_inserted} записей")
    return total_inserted


def collect_amazon(conn, writer, normalizer, deduplicator, run_id: str):
    """Сбор данных с Amazon US"""
    log.info("=" * 50)
    log.info("Начинаем сбор данных с Amazon...")
    log.info("=" * 50)

    client = AmazonClient()
    today = str(date.today())
    total_inserted = 0

    for category in ["GPU", "CPU", "RAM"]:
        try:
            source_id = SOURCE_IDS["amazon_us"]

            # Amazon — поиск по категории (экономим запросы)
            listings = client.search_category(category, region="US")

            if not listings:
                continue

            # Сохраняем сырые данные
            raw_data = [
                {"title": l.title, "price": l.price, "currency": l.currency,
                 "asin": l.item_id, "url": l.item_url}
                for l in listings
            ]
            raw_id = writer.save_raw(source_id, f"Amazon {category}", raw_data, run_id)

            # Нормализуем
            normalized, skipped = normalizer.normalize_batch(
                listings, source_id=source_id,
                date_id=today, etl_run_id=run_id
            )

            # Дедупликация
            unique = deduplicator.deduplicate(normalized)
            unique = deduplicator.filter_existing(unique, conn)

            # Сохраняем
            inserted, dup = writer.save_normalized(unique)
            conn.commit()
            total_inserted += inserted

        except Exception as e:
            log.error(f"Ошибка при сборе Amazon {category}: {e}")
            conn.rollback()

    log.info(f"Amazon завершён. Всего вставлено: {total_inserted} записей")
    return total_inserted


def main():
    parser = argparse.ArgumentParser(description="Сбор цен на железо")
    parser.add_argument("--source", choices=["ebay", "amazon", "all"], default="all")
    args = parser.parse_args()

    run_id = f"manual_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    log.info(f"Запуск сбора данных. run_id={run_id}")
    log.info(f"Источник: {args.source}")

    conn = get_connection()
    writer = Writer(conn)

    # Загружаем продукты и инициализируем трансформеры
    products = load_products(conn)
    exchange = ExchangeRateClient()
    normalizer = Normalizer(products, exchange)
    deduplicator = Deduplicator()

    total = 0

    try:
        if args.source in ("ebay", "all"):
            total += collect_ebay(conn, writer, normalizer, deduplicator, run_id)

        if args.source in ("amazon", "all"):
            total += collect_amazon(conn, writer, normalizer, deduplicator, run_id)

        # Логируем результат в etl_runs
        writer.log_etl_run(
            dag_id=f"manual_{args.source}",
            status="success",
            records_inserted=total,
            run_id=run_id,
        )
        conn.commit()

    except Exception as e:
        log.error(f"Критическая ошибка: {e}")
        writer.log_etl_run(
            dag_id=f"manual_{args.source}",
            status="failed",
            error_message=str(e),
            run_id=run_id,
        )
        conn.commit()

    finally:
        conn.close()

    log.info("=" * 50)
    log.info(f"Сбор завершён. Всего записей в БД сегодня: {total}")
    log.info(f"Проверь в Supabase → Table Editor → fact_price_history")
    log.info("=" * 50)


if __name__ == "__main__":
    main()