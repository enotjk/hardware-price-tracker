"""
Products router — эндпоинты для работы с продуктами
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from database import execute_query

router = APIRouter(prefix="/products", tags=["Products"])


@router.get("")
async def get_products(
    category: Optional[str] = Query(None, description="GPU, CPU, RAM"),
    brand: Optional[str] = Query(None, description="NVIDIA, AMD, Intel"),
):
    """Список всех отслеживаемых продуктов с фильтрами"""
    sql = """
        SELECT product_id, name, brand, category, model_number, msrp_usd, release_date
        FROM dim_products
        WHERE is_active = true
    """
    params = []

    if category:
        sql += " AND category = %s"
        params.append(category.upper())

    if brand:
        sql += " AND brand = %s"
        params.append(brand)

    sql += " ORDER BY category, brand, name"

    return execute_query(sql, params or None)


@router.get("/search")
async def search_products(q: str = Query(..., min_length=2)):
    """Поиск продуктов по названию"""
    sql = """
        SELECT product_id, name, brand, category, model_number, msrp_usd
        FROM dim_products
        WHERE is_active = true
          AND (name ILIKE %s OR model_number ILIKE %s)
        ORDER BY name
        LIMIT 20
    """
    pattern = f"%{q}%"
    return execute_query(sql, (pattern, pattern))


@router.get("/{product_id}")
async def get_product(product_id: str):
    """Детали конкретного продукта"""
    sql = """
        SELECT product_id, name, brand, category, model_number,
               msrp_usd, tdp_watts, vram_gb, cores, release_date
        FROM dim_products
        WHERE product_id = %s AND is_active = true
    """
    rows = execute_query(sql, (product_id,))
    if not rows:
        raise HTTPException(status_code=404, detail="Продукт не найден")
    return rows[0]