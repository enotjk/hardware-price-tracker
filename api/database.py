"""
Подключение к Supabase PostgreSQL для FastAPI
Используем connection pool для эффективной работы с БД
"""

from dotenv import load_dotenv
from pathlib import Path

# Загружаем .env из корня проекта
load_dotenv(Path(__file__).parent.parent / ".env")

import os
import logging
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2 import pool

log = logging.getLogger(__name__)

# Connection pool — держим несколько соединений открытыми
_pool = None


def get_pool():
    """Инициализирует и возвращает connection pool"""
    global _pool
    if _pool is None:
        db_url = os.getenv("DIRECT_URL")
        if not db_url:
            raise ValueError("DIRECT_URL должен быть задан в .env")

        _pool = psycopg2.pool.SimpleConnectionPool(
            minconn=1,
            maxconn=10,
            dsn=db_url,
        )
        log.info("Database connection pool создан")
    return _pool


def get_connection():
    """Берёт соединение из пула"""
    return get_pool().getconn()


def release_connection(conn):
    """Возвращает соединение в пул"""
    get_pool().putconn(conn)


def execute_query(sql: str, params=None) -> list[dict]:
    """
    Выполняет SELECT запрос и возвращает список словарей.
    Автоматически берёт и возвращает соединение в пул.

    Args:
        sql:    SQL запрос
        params: параметры запроса (защита от SQL injection)

    Returns:
        Список строк как dict
    """
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    finally:
        release_connection(conn)


def test_connection() -> bool:
    """Проверяет подключение к БД"""
    try:
        rows = execute_query("SELECT COUNT(*) as count FROM dim_products")
        count = rows[0]["count"] if rows else 0
        log.info(f"DB OK — {count} продуктов в справочнике")
        return True
    except Exception as e:
        log.error(f"DB Error: {e}")
        return False