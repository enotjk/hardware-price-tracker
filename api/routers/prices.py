"""
Prices router — эндпоинты для цен
"""

import time
import logging
from fastapi import APIRouter, Query
from typing import Optional
from database import execute_query
from schemas import PriceHistorySchema, CurrentPriceSchema, TopMoverSchema

log = logging.getLogger(__name__)
router = APIRouter(prefix="/prices", tags=["Prices"])

_cache: dict = {}
CACHE_TTL = 30 * 60


def _get_cached(key: str):
    if key in _cache:
        entry = _cache[key]
        if time.time() < entry["expires_at"]:
            return entry["data"]
        else:
            del _cache[key]
    return None


def _set_cache(key: str, data):
    _cache[key] = {
        "data": data,
        "expires_at": time.time() + CACHE_TTL,
    }


@router.get("/history/{product_id}", response_model=list[PriceHistorySchema])
async def get_price_history(
    product_id: str,
    days: int = Query(30, ge=1, le=365),
    source_id: Optional[int] = Query(None),
):
    sql = """
        SELECT
            f.date_id,
            f.price_usd,
            f.price_original,
            f.currency,
            ds.name         as source_name,
            ds.display_name,
            ds.region
        FROM fact_price_history f
        JOIN dim_sources ds ON f.source_id = ds.source_id
        WHERE f.product_id = %s::uuid
          AND f.date_id >= CURRENT_DATE - INTERVAL '%s days'
    """
    params = [product_id, days]
    if source_id:
        sql += " AND f.source_id = %s"
        params.append(source_id)
    sql += " ORDER BY f.date_id ASC, ds.region"
    return execute_query(sql, params)


@router.get("/current/{product_id}", response_model=list[CurrentPriceSchema])
async def get_current_prices(product_id: str):
    cache_key = f"current_prices:{product_id}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached
    sql = """
        SELECT
            product_id::text,
            source_name,
            source_name as display_name,
            region,
            price_usd,
            date_id,
            collected_at,
            product_url
        FROM mart_current_prices
        WHERE product_id = %s::uuid
        ORDER BY price_usd ASC
    """
    data = execute_query(sql, (product_id,))
    _set_cache(cache_key, data)
    return data


@router.get("/top-movers", response_model=list[TopMoverSchema])
async def get_top_movers(
    limit: int = Query(10, ge=1, le=50),
):
    cache_key = f"top_movers:{limit}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached
    sql = """
        SELECT
            product_id::text,
            product_name,
            NULL::text as brand,
            category,
            current_price,
            previous_price,
            price_change_pct,
            price_change_abs
        FROM mart_top_movers
        ORDER BY ABS(price_change_pct) DESC
        LIMIT %s
    """
    data = execute_query(sql, (limit,))
    _set_cache(cache_key, data)
    return data


@router.get("/changes", response_model=list[TopMoverSchema])
async def get_price_changes(
    category: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
):
    sql = """
        SELECT
            product_id::text,
            product_name,
            NULL::text as brand,
            category,
            current_price,
            previous_price,
            price_change_pct,
            price_change_abs
        FROM mart_price_changes
        WHERE 1=1
    """
    params = []
    if category:
        sql += " AND category = %s"
        params.append(category.upper())
    sql += " ORDER BY ABS(price_change_pct) DESC NULLS LAST LIMIT %s"
    params.append(limit)
    return execute_query(sql, params)