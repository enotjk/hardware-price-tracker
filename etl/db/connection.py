"""
Подключение к базе данных
Используем DIRECT_URL (без pgbouncer) для прямых запросов из Python скриптов.
DATABASE_URL (с pgbouncer) будет использоваться только в продакшне на Railway.
"""

import os
import logging
import psycopg2
from psycopg2.extras import RealDictCursor

log = logging.getLogger(__name__)


def get_connection():
    """
    Возвращает psycopg2 подключение к Supabase PostgreSQL.
    Использует DIRECT_URL из .env

    Использование:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT ...")
        conn.commit()
        conn.close()

    Или через context manager:
        with get_connection() as conn:
            ...
    """
    db_url = os.getenv("DIRECT_URL")

    if not db_url:
        raise ValueError("DIRECT_URL должен быть задан в .env")

    try:
        conn = psycopg2.connect(db_url)
        log.debug("Подключение к БД установлено")
        return conn
    except Exception as e:
        log.error(f"Ошибка подключения к БД: {e}")
        raise


def test_connection() -> bool:
    """Проверяет что подключение работает. Возвращает True/False."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM dim_products")
        count = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        log.info(f"Подключение OK — в dim_products {count} продуктов")
        return True
    except Exception as e:
        log.error(f"Тест подключения провалился: {e}")
        return False


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    logging.basicConfig(level=logging.INFO)
    test_connection()