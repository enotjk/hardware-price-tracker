"""
Prices router — эндпоинты для цен
"""

from fastapi import APIRouter, Query
from typing import Optional
from database import execute_query

router = APIRouter(prefix="/prices", tags=["Prices"])


@router.get("/history/{product_id}")
async def get_price_history(
    product_id: str,
    days: int = Query(30, ge=1, le=365),
    source_id: Optional[int] = None,
):
    """
    История цены продукта за период.
    Используется для построения графика на фронте.
    """
    sql = """
        SELECT
            date_id,
            price_usd,
            price_original,
            currency,
            ds.name        as source_name,
            ds.display_name,
            ds.region
        FROM fact_price_history f
        JOIN dim_sources ds ON f.source_id = ds.source_id
        WHERE f.product_id = %s
          AND f.date_id >= CURRENT_DATE - INTERVAL '%s days'
    """
    params = [product_id, days]

    if source_id:
        sql += " AND f.source_id = %s"
        params.append(source_id)

    sql += " ORDER BY date_id ASC, ds.region"

    return execute_query(sql, params)


@router.get("/current/{product_id}")
async def get_current_prices(product_id: str):
    """
    Текущие цены продукта по всем источникам.
    Используется для таблицы магазинов на странице продукта.
    """
    sql = """
        SELECT
            product_id,
            source_name,
            display_name,
            region,
            price_usd,
            date_id,
            collected_at
        FROM mart_current_prices
        WHERE product_id = %s
        ORDER BY price_usd ASC
    """
    return execute_query(sql, (product_id,))


@router.get("/top-movers")
async def get_top_movers(limit: int = Query(10, ge=1, le=50)):
    """
    Топ продуктов с наибольшим изменением цены за 7 дней.
    Используется для виджета на главной странице.
    """
    sql = """
        SELECT
            product_id,
            product_name,
            brand,
            category,
            current_price,
            previous_price,
            price_change_pct,
            price_change_abs
        FROM mart_top_movers
        ORDER BY ABS(price_change_pct) DESC
        LIMIT %s
    """
    return execute_query(sql, (limit,))


@router.get("/changes")
async def get_price_changes(
    category: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100),
):
    """
    Изменения цен по всем продуктам.
    """
    sql = """
        SELECT
            product_id,
            product_name,
            brand,
            category,
            current_price,
            price_change_pct,
            price_change_abs,
            vs_msrp_pct
        FROM mart_price_changes
        WHERE 1=1
    """
    params = []

    if category:
        sql += " AND category = %s"
        params.append(category.upper())

    sql += " ORDER BY ABS(price_change_pct) DESC LIMIT %s"
    params.append(limit)

    return execute_query(sql, params)