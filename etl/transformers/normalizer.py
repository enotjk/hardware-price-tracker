"""
Normalizer — нормализация сырых данных из API
Что делает:
- Связывает листинг с продуктом из dim_products по ключевым словам в title
- Конвертирует цену в USD через ExchangeRateClient
- Возвращает готовую запись для fact_price_history
"""

import logging
import re
from dataclasses import dataclass
from typing import Optional

log = logging.getLogger(__name__)


@dataclass
class NormalizedPrice:
    """Готовая запись для вставки в fact_price_history"""
    product_id: str
    source_id: int
    date_id: str                    # YYYY-MM-DD
    price_usd: float
    price_original: float
    currency: str
    exchange_rate: float
    in_stock: bool
    seller_name: Optional[str]
    product_url: Optional[str]
    listing_title: str
    etl_run_id: Optional[str]
    raw_price_id: Optional[str]


class Normalizer:
    """
    Нормализует сырые листинги в записи для БД.

    Использование:
        normalizer = Normalizer(db_products, exchange_client)
        record = normalizer.normalize(listing, source_id=1, etl_run_id="run_123")
    """

    def __init__(self, products: list[dict], exchange_client):
        """
        Args:
            products:        список продуктов из dim_products
            exchange_client: экземпляр ExchangeRateClient
        """
        self.products = products
        self.exchange = exchange_client
        self._product_index = self._build_index(products)

    # ─────────────────────────────────────
    # Построение индекса продуктов
    # ─────────────────────────────────────
    def _build_index(self, products: list[dict]) -> dict:
        """
        Строит словарь для поиска продукта по model_number.
        Ключи — нормализованные model_number в нижнем регистре.
        """
        index = {}
        for product in products:
            model = product.get("model_number", "")
            if model:
                key = self._normalize_text(model)
                index[key] = product
                log.debug(f"Индекс: '{key}' → {product['name']}")

        log.info(f"Индекс продуктов построен: {len(index)} записей")
        return index

    # ─────────────────────────────────────
    # Поиск продукта по названию листинга
    # ─────────────────────────────────────
    def find_product(self, title: str) -> Optional[dict]:
        """
        Ищет продукт в индексе по названию листинга.

        Стратегия:
        1. Точный поиск — model_number целиком в title (GPU/CPU)
        2. Токенный поиск — все слова из model_number есть в title (RAM)

        Args:
            title: название листинга из API

        Returns:
            dict продукта или None если не найден
        """
        normalized_title = self._normalize_text(title)

        # Шаг 1: точный поиск по model_number
        # Сортируем по длине — более длинные модели проверяем первыми
        # чтобы "RTX 4070 Ti Super" нашёлся раньше чем "RTX 4070"
        sorted_keys = sorted(self._product_index.keys(), key=len, reverse=True)

        for key in sorted_keys:
            if key in normalized_title:
                product = self._product_index[key]
                log.debug(f"Найден продукт (точный): '{key}' в '{title[:50]}...'")
                return product

        # Шаг 2: токенный поиск для RAM
        # "ddr5 6000 32gb" → проверяем что все три слова есть в title
        for key, product in self._product_index.items():
            if product.get("category") != "RAM":
                continue

            tokens = key.split()
            if len(tokens) < 2:
                continue

            if all(token in normalized_title for token in tokens):
                log.debug(f"Найден продукт (токены {tokens}): '{title[:50]}...'")
                return product

        log.warning(f"Продукт не найден для: '{title[:60]}...'")
        return None

    # ─────────────────────────────────────
    # Нормализация одного листинга
    # ─────────────────────────────────────
    def normalize(
        self,
        listing,
        source_id: int,
        date_id: str,
        etl_run_id: Optional[str] = None,
        raw_price_id: Optional[str] = None,
    ) -> Optional[NormalizedPrice]:
        """
        Нормализует один листинг в запись для fact_price_history.

        Returns:
            NormalizedPrice или None если листинг не прошёл валидацию
        """
        # 1. Валидация
        if not self._is_valid(listing):
            return None

        # 2. Найти продукт в справочнике
        product = self.find_product(listing.title)
        if not product:
            return None

        # 3. Конвертация цены в USD
        if listing.currency == "USD":
            price_usd = listing.price
            exchange_rate = 1.0
        else:
            exchange_rate = self.exchange.get_rate(listing.currency, "USD")
            price_usd = self.exchange.convert(listing.price, listing.currency)

        # 4. Собираем нормализованную запись
        return NormalizedPrice(
            product_id=str(product["product_id"]),
            source_id=source_id,
            date_id=date_id,
            price_usd=round(price_usd, 2),
            price_original=listing.price,
            currency=listing.currency,
            exchange_rate=exchange_rate,
            in_stock=listing.availability == "IN_STOCK",
            seller_name=listing.seller_name,
            product_url=listing.item_url,
            listing_title=listing.title,
            etl_run_id=etl_run_id,
            raw_price_id=raw_price_id,
        )

    def normalize_batch(
        self,
        listings: list,
        source_id: int,
        date_id: str,
        etl_run_id: Optional[str] = None,
    ) -> tuple[list[NormalizedPrice], int]:
        """
        Нормализует список листингов.

        Returns:
            (список успешно нормализованных, кол-во пропущенных)
        """
        results = []
        skipped = 0

        for listing in listings:
            record = self.normalize(listing, source_id, date_id, etl_run_id)
            if record:
                results.append(record)
            else:
                skipped += 1

        log.info(f"Нормализация: {len(results)} успешно, {skipped} пропущено")
        return results, skipped

    # ─────────────────────────────────────
    # Вспомогательные методы
    # ─────────────────────────────────────
    def _is_valid(self, listing) -> bool:
        """Проверяет что листинг валиден перед обработкой"""
        if not listing.title:
            log.debug("Пропуск: пустой title")
            return False

        if not listing.price or listing.price <= 0:
            log.debug(f"Пропуск: некорректная цена {listing.price}")
            return False

        if listing.price > 10000:
            log.debug(f"Пропуск: подозрительно высокая цена {listing.price}")
            return False

        if not listing.currency:
            log.debug("Пропуск: отсутствует валюта")
            return False

        return True

    @staticmethod
    def _normalize_text(text: str) -> str:
        """Приводит текст к нижнему регистру, убирает лишние символы"""
        text = text.lower()
        text = re.sub(r'[^\w\s]', ' ', text)   # убираем пунктуацию
        text = re.sub(r'\s+', ' ', text)         # схлопываем пробелы
        return text.strip()