"""
Pydantic схемы — описывают структуру данных которые API принимает и возвращает.
Зачем нужны:
- Автоматическая валидация данных из БД
- Красивая документация в Swagger UI
- Автодополнение в IDE на фронтенде (TypeScript типы генерируются из них)
"""

from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime
from decimal import Decimal


# ─────────────────────────────────────────
# Products
# ─────────────────────────────────────────
class ProductSchema(BaseModel):
    product_id: str
    name: str
    brand: str
    category: str
    model_number: Optional[str] = None
    msrp_usd: Optional[Decimal] = None
    tdp_watts: Optional[int] = None
    vram_gb: Optional[int] = None
    cores: Optional[int] = None
    release_date: Optional[date] = None

    class Config:
        from_attributes = True


class ProductListSchema(BaseModel):
    product_id: str
    name: str
    brand: str
    category: str
    model_number: Optional[str] = None
    msrp_usd: Optional[Decimal] = None

    class Config:
        from_attributes = True


# ─────────────────────────────────────────
# Prices
# ─────────────────────────────────────────
class PriceHistorySchema(BaseModel):
    date_id: date
    price_usd: Decimal
    price_original: Decimal
    currency: str
    source_name: str
    display_name: str
    region: str

    class Config:
        from_attributes = True


class CurrentPriceSchema(BaseModel):
    product_id: str
    source_name: str
    display_name: str
    region: str
    price_usd: Decimal
    date_id: date
    collected_at: Optional[datetime] = None
    product_url: Optional[str] = None

    class Config:
        from_attributes = True


class TopMoverSchema(BaseModel):
    product_id: str
    product_name: str
    brand: Optional[str] = None
    category: str
    current_price: Optional[Decimal] = None
    previous_price: Optional[Decimal] = None
    price_change_pct: Optional[Decimal] = None
    price_change_abs: Optional[Decimal] = None

    class Config:
        from_attributes = True


# ─────────────────────────────────────────
# Pipelines
# ─────────────────────────────────────────
class PipelineSchema(BaseModel):
    dag_id: str
    status: str
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    records_fetched: Optional[int] = None
    records_inserted: Optional[int] = None
    error_message: Optional[str] = None

    class Config:
        from_attributes = True


class StatsSchema(BaseModel):
    total_price_records: int
    total_raw_records: int
    tracked_products: int
    last_collected_at: Optional[datetime] = None
    successful_runs: int
    failed_runs: int

    class Config:
        from_attributes = True