"""
Hardware Price Tracker — FastAPI Backend
Читает данные из dbt витрин в Supabase и отдаёт фронтенду.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import os

log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Запускается при старте и остановке приложения"""
    log.info("Hardware Price Tracker API запущен")
    yield
    log.info("API остановлен")


app = FastAPI(
    title="Hardware Price Tracker API",
    description="API для отслеживания цен на компьютерное железо",
    version="0.1.0",
    lifespan=lifespan,
)

# ─────────────────────────────────────────
# CORS — разрешаем запросы с фронтенда
# ─────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",        # Next.js локально
        "https://*.vercel.app",         # Vercel деплой
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────
# Подключаем роутеры
# ─────────────────────────────────────────
from routers import products, prices, pipelines

app.include_router(products.router)
app.include_router(prices.router)
app.include_router(pipelines.router)


# ─────────────────────────────────────────
# Health check
# ─────────────────────────────────────────
@app.get("/health", tags=["System"])
async def health():
    """Проверка что API работает и БД доступна"""
    from database import test_connection
    db_ok = test_connection()
    return {
        "status": "ok" if db_ok else "degraded",
        "db": "connected" if db_ok else "error",
        "version": "0.1.0",
    }


@app.get("/", tags=["System"])
async def root():
    return {"message": "Hardware Price Tracker API", "docs": "/docs"}