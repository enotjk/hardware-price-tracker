"""
Amazon клиент через RapidAPI (Real-Time Amazon Data)
Документация: https://rapidapi.com/real-time-amazon-data

Стратегия запросов (экономим лимит 100/мес):
- Не делаем запрос на каждый продукт отдельно
- Делаем 1 запрос на категорию: "RTX GPU", "AMD Ryzen CPU", "DDR5 RAM"
- Из результатов парсим все найденные продукты за раз
- Итого: ~6 запросов за запуск (3 категории × 2 региона US/DE)
"""
from __future__ import annotations

import os
import time
import logging
import requests
from dataclasses import dataclass
from typing import Optional

log = logging.getLogger(__name__)


# ─────────────────────────────────────────
# Поисковые запросы по категориям
# Широкие запросы чтобы поймать много товаров за один запрос
# ─────────────────────────────────────────
SEARCH_QUERIES = {
    "GPU": [
        "RTX 4090 graphics card",
        "RTX 4080 graphics card",
        "RX 7900 graphics card",
    ],
    "CPU": [
        "Intel Core i9 i7 processor",
        "AMD Ryzen 9 7 processor",
    ],
    "RAM": [
        "DDR5 32GB desktop memory",
        "DDR4 32GB desktop memory",
    ],
}

# ─────────────────────────────────────────
# Настройки регионов Amazon
# ─────────────────────────────────────────
AMAZON_REGIONS = {
    "US": {"country": "US", "currency": "USD"},
    "DE": {"country": "DE", "currency": "EUR"},
}


@dataclass
class PriceListing:
    """Один листинг с ценой — совместим с eBay клиентом"""
    title: str
    price: float
    currency: str
    region: str
    source: str = "amazon"
    availability: str = "IN_STOCK"
    seller_name: Optional[str] = None
    item_url: Optional[str] = None
    item_id: Optional[str] = None       # ASIN для Amazon
    image_url: Optional[str] = None
    rating: Optional[float] = None
    reviews_count: Optional[int] = None


class AmazonClient:
    """
    Клиент для Amazon через RapidAPI.

    Использование:
        client = AmazonClient()
        listings = client.search_category("GPU", region="US")
    """

    BASE_URL = "https://real-time-amazon-data.p.rapidapi.com"

    def __init__(self):
        self.api_key = os.getenv("RAPIDAPI_KEY")
        self.host = os.getenv("RAPIDAPI_AMAZON_HOST", "real-time-amazon-data.p.rapidapi.com")

        if not self.api_key:
            raise ValueError("RAPIDAPI_KEY должен быть задан в .env")

        self.headers = {
            "X-RapidAPI-Key": self.api_key,
            "X-RapidAPI-Host": self.host,
            "Content-Type": "application/json",
        }

        # Счётчик запросов — следим за лимитом
        self._request_count = 0

    # ─────────────────────────────────────
    # Поиск по категории
    # ─────────────────────────────────────
    def search_category(
        self,
        category: str,
        region: str = "US",
    ) -> list[PriceListing]:
        """
        Ищет все продукты категории на Amazon.
        Делает несколько запросов по разным query из SEARCH_QUERIES.

        Args:
            category: 'GPU', 'CPU', или 'RAM'
            region:   'US' или 'DE'

        Returns:
            Список PriceListing со всеми найденными товарами
        """
        queries = SEARCH_QUERIES.get(category, [])
        if not queries:
            raise ValueError(f"Неизвестная категория: {category}")

        region_config = AMAZON_REGIONS.get(region)
        if not region_config:
            raise ValueError(f"Неизвестный регион: {region}")

        all_listings = []

        for query in queries:
            log.info(f"Amazon {region}: поиск '{query}'")
            listings = self._search(query, region_config, region)
            all_listings.extend(listings)

            # Пауза между запросами — не спамим API
            time.sleep(2)

        log.info(f"Amazon {region} {category}: найдено {len(all_listings)} листингов")
        return all_listings

    # ─────────────────────────────────────
    # Базовый поиск
    # ─────────────────────────────────────
    def _search(
        self,
        query: str,
        region_config: dict,
        region: str,
        page: int = 1,
    ) -> list[PriceListing]:
        """Один поисковый запрос к Amazon через RapidAPI"""

        params = {
            "query": query,
            "page": str(page),
            "country": region_config["country"],
            "sort_by": "RELEVANCE",
            "product_condition": "NEW",
        }

        try:
            response = self._request_with_retry(
                f"{self.BASE_URL}/search",
                params=params,
            )
            self._request_count += 1
            log.debug(f"Использовано запросов RapidAPI: {self._request_count}")

            data = response.json()
            products = data.get("data", {}).get("products", [])

            return [
                self._parse_product(p, region, region_config["currency"])
                for p in products
                if self._has_price(p)
            ]

        except Exception as e:
            log.error(f"Ошибка поиска Amazon '{query}': {e}")
            return []

    # ─────────────────────────────────────
    # Retry логика
    # ─────────────────────────────────────
    def _request_with_retry(
        self,
        url: str,
        params: dict,
        max_retries: int = 3,
        delay: int = 5,
    ) -> requests.Response:
        """GET запрос с повторами при ошибке"""
        last_error = None

        for attempt in range(1, max_retries + 1):
            try:
                response = requests.get(
                    url,
                    headers=self.headers,
                    params=params,
                    timeout=30,
                )

                if response.status_code == 429:
                    wait = delay * attempt
                    log.warning(f"Rate limit RapidAPI. Ждём {wait} сек...")
                    time.sleep(wait)
                    continue

                if response.status_code == 403:
                    log.error("RapidAPI: нет доступа. Проверь подписку на API.")
                    raise Exception("RapidAPI 403: доступ запрещён")

                response.raise_for_status()
                return response

            except requests.RequestException as e:
                last_error = e
                if attempt < max_retries:
                    log.warning(f"Попытка {attempt}/{max_retries}: {e}. Повтор через {delay} сек...")
                    time.sleep(delay)

        raise last_error

    # ─────────────────────────────────────
    # Парсинг продукта
    # ─────────────────────────────────────
    def _parse_product(self, product: dict, region: str, currency: str) -> PriceListing:
        """Парсит один продукт из ответа RapidAPI"""

        # Цена может быть в разных полях
        price = 0.0
        price_str = (
            product.get("product_price") or
            product.get("product_original_price") or
            "0"
        )
        # Убираем символы валюты и запятые: "$1,749.99" → 1749.99
        price_clean = price_str.replace("$", "").replace("€", "").replace(",", "").strip()
        try:
            price = float(price_clean)
        except (ValueError, AttributeError):
            price = 0.0

        # URL продукта
        asin = product.get("asin", "")
        domain = "amazon.com" if region == "US" else "amazon.de"
        item_url = f"https://www.{domain}/dp/{asin}" if asin else None

        return PriceListing(
            title=product.get("product_title", ""),
            price=price,
            currency=currency,
            region=region,
            source="amazon",
            availability="IN_STOCK" if product.get("is_prime") or price > 0 else "OUT_OF_STOCK",
            item_url=item_url,
            item_id=asin,
            image_url=product.get("product_photo"),
            rating=float(product.get("product_star_rating") or 0) or None,
            reviews_count=int(product.get("product_num_ratings") or 0) or None,
        )

    @staticmethod
    def _has_price(product: dict) -> bool:
        """Проверяет что у продукта есть цена"""
        return bool(
            product.get("product_price") or
            product.get("product_original_price")
        )

    def get_request_count(self) -> int:
        """Возвращает кол-во использованных запросов в этой сессии"""
        return self._request_count


# ─────────────────────────────────────────
# Быстрый тест:
# PYTHONPATH=etl/extractors python etl/extractors/amazon.py
# ─────────────────────────────────────────
if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    logging.basicConfig(level=logging.INFO)

    client = AmazonClient()

    print("\n=== Тест: поиск GPU на Amazon US ===")
    listings = client.search_category("GPU", region="US")

    print(f"\nНайдено листингов: {len(listings)}")
    for i, item in enumerate(listings[:5], 1):
        print(f"\n{i}. {item.title[:60]}...")
        print(f"   Цена:    {item.price} {item.currency}")
        print(f"   ASIN:    {item.item_id}")
        print(f"   Рейтинг: {item.rating} ({item.reviews_count} отзывов)")

    print(f"\nИспользовано запросов RapidAPI: {client.get_request_count()}")