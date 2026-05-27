"""
eBay Browse API клиент
Документация: https://developer.ebay.com/api-docs/buy/browse/overview.html
 
Что делает:
- Авторизуется через OAuth (Client Credentials)
- Ищет товары по названию и категории
- Возвращает список листингов с ценами
- Поддерживает США (ebay.com) и Германию (ebay.de)
"""
 
import os
import time
import logging
import requests
from dataclasses import dataclass
from typing import Optional
 
log = logging.getLogger(__name__)
 
 
# ─────────────────────────────────────────
# Категории eBay для нашего железа
# ─────────────────────────────────────────
EBAY_CATEGORIES = {
    "GPU": "27386",   # Graphics/Video Cards
    "CPU": "164",     # Processors
    "RAM": "170083",  # Computer Memory (RAM)
}
 
# ─────────────────────────────────────────
# Настройки для каждого региона
# ─────────────────────────────────────────
EBAY_REGIONS = {
    "US": {
        "marketplace_id": "EBAY_US",
        "api_url": "https://api.ebay.com",
        "currency": "USD",
    },
    "DE": {
        "marketplace_id": "EBAY_DE",
        "api_url": "https://api.ebay.com",  # API один, регион передаём в заголовке
        "currency": "EUR",
    },
}
 
 
@dataclass
class PriceListing:
    """Один листинг с ценой — результат поиска"""
    title: str
    price: float
    currency: str
    region: str
    source: str = "ebay"
    availability: str = "IN_STOCK"
    seller_name: Optional[str] = None
    item_url: Optional[str] = None
    item_id: Optional[str] = None
    condition: Optional[str] = None         # 'New', 'Used', 'Refurbished'
    image_url: Optional[str] = None
 
 
class EbayClient:
    """
    Клиент для eBay Browse API.
 
    Использование:
        client = EbayClient()
        listings = client.search("RTX 4090", category="GPU", region="US")
    """
 
    AUTH_URL = "https://api.ebay.com/identity/v1/oauth2/token"
    SEARCH_URL = "https://api.ebay.com/buy/browse/v1/item_summary/search"
 
    def __init__(self):
        self.client_id = os.getenv("EBAY_CLIENT_ID")
        self.client_secret = os.getenv("EBAY_CLIENT_SECRET")
 
        if not self.client_id or not self.client_secret:
            raise ValueError(
                "EBAY_CLIENT_ID и EBAY_CLIENT_SECRET должны быть заданы в .env"
            )
 
        # Кеш токена — не запрашиваем новый при каждом вызове
        self._token: Optional[str] = None
        self._token_expires_at: float = 0
 
    # ─────────────────────────────────────
    # Авторизация
    # ─────────────────────────────────────
    def _get_token(self) -> str:
        """
        Получает OAuth токен через Client Credentials flow.
        Кеширует токен до истечения срока действия.
        """
        # Если токен ещё валиден — возвращаем его
        if self._token and time.time() < self._token_expires_at - 60:
            return self._token
 
        log.info("Запрашиваем новый eBay OAuth токен...")
 
        response = requests.post(
            self.AUTH_URL,
            auth=(self.client_id, self.client_secret),
            data={
                "grant_type": "client_credentials",
                "scope": "https://api.ebay.com/oauth/api_scope",
            },
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
 
        self._token = data["access_token"]
        self._token_expires_at = time.time() + data["expires_in"]
 
        log.info(f"Токен получен, действует {data['expires_in']} секунд")
        return self._token
 
    # ─────────────────────────────────────
    # Поиск товаров
    # ─────────────────────────────────────
    def search(
        self,
        query: str,
        category: str = "GPU",
        region: str = "US",
        limit: int = 50,
        only_new: bool = True,
    ) -> list[PriceListing]:
        """
        Ищет товары на eBay по запросу.
 
        Args:
            query:     поисковый запрос, например 'RTX 4090'
            category:  'GPU', 'CPU', или 'RAM'
            region:    'US' или 'DE'
            limit:     максимум листингов (до 200)
            only_new:  только новые товары (не б/у)
 
        Returns:
            Список PriceListing с ценами и деталями
        """
        region_config = EBAY_REGIONS.get(region)
        if not region_config:
            raise ValueError(f"Неизвестный регион: {region}. Доступны: US, DE")
 
        category_id = EBAY_CATEGORIES.get(category)
        if not category_id:
            raise ValueError(f"Неизвестная категория: {category}. Доступны: GPU, CPU, RAM")
 
        token = self._get_token()
 
        params = {
            "q": query,
            "category_ids": category_id,
            "limit": min(limit, 200),       # eBay максимум 200 за запрос
            "sort": "price",                # сортировка по цене
        }
 
        # Фильтр только новых товаров
        if only_new:
            params["filter"] = "conditions:{NEW}"
 
        headers = {
            "Authorization": f"Bearer {token}",
            "X-EBAY-C-MARKETPLACE-ID": region_config["marketplace_id"],
            "X-EBAY-C-ENDUSERCTX": "contextualLocation=country=US",
            "Content-Type": "application/json",
        }
 
        log.info(f"Поиск на eBay {region}: '{query}' (категория {category})")
 
        response = self._request_with_retry(self.SEARCH_URL, headers=headers, params=params)
        data = response.json()
 
        items = data.get("itemSummaries", [])
        log.info(f"Найдено {len(items)} листингов для '{query}' на eBay {region}")
 
        return [self._parse_item(item, region) for item in items]
 
    # ─────────────────────────────────────
    # Retry логика
    # ─────────────────────────────────────
    def _request_with_retry(
        self,
        url: str,
        headers: dict,
        params: dict,
        max_retries: int = 3,
        delay: int = 5,
    ) -> requests.Response:
        """
        Делает GET запрос с повторами при ошибке.
        При ошибке ждёт delay секунд и пробует снова.
        """
        last_error = None
 
        for attempt in range(1, max_retries + 1):
            try:
                response = requests.get(url, headers=headers, params=params, timeout=30)
 
                if response.status_code == 429:
                    # Rate limit — ждём дольше
                    wait = delay * attempt
                    log.warning(f"Rate limit eBay API. Ждём {wait} сек...")
                    time.sleep(wait)
                    continue
 
                response.raise_for_status()
                return response
 
            except requests.RequestException as e:
                last_error = e
                if attempt < max_retries:
                    log.warning(f"Попытка {attempt}/{max_retries} не удалась: {e}. Повтор через {delay} сек...")
                    time.sleep(delay)
                else:
                    log.error(f"Все {max_retries} попытки исчерпаны")
 
        raise last_error
 
    # ─────────────────────────────────────
    # Парсинг ответа
    # ─────────────────────────────────────
    def _parse_item(self, item: dict, region: str) -> PriceListing:
        """Парсит один элемент из ответа eBay API в PriceListing"""
 
        # Цена — может быть в разных полях
        price_info = item.get("price", {})
        price = float(price_info.get("value", 0))
        currency = price_info.get("currency", EBAY_REGIONS[region]["currency"])
 
        # Продавец
        seller = item.get("seller", {})
        seller_name = seller.get("username")
 
        # Изображение
        image = item.get("image", {})
        image_url = image.get("imageUrl")
 
        # Наличие
        availability = "IN_STOCK"
        buying_options = item.get("buyingOptions", [])
        if "FIXED_PRICE" not in buying_options and "AUCTION" not in buying_options:
            availability = "OUT_OF_STOCK"
 
        return PriceListing(
            title=item.get("title", ""),
            price=price,
            currency=currency,
            region=region,
            source="ebay",
            availability=availability,
            seller_name=seller_name,
            item_url=item.get("itemWebUrl"),
            item_id=item.get("itemId"),
            condition=item.get("condition"),
            image_url=image_url,
        )
 
 
# ─────────────────────────────────────────
# Быстрый тест — запускай напрямую:
# python etl/extractors/ebay.py
# ─────────────────────────────────────────
if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
 
    logging.basicConfig(level=logging.INFO)
 
    client = EbayClient()
 
    print("\n=== Тест: поиск RTX 4090 на eBay US ===")
    listings = client.search("RTX 4090", category="GPU", region="US", limit=5)
 
    for i, item in enumerate(listings, 1):
        print(f"\n{i}. {item.title[:60]}...")
        print(f"   Цена:    {item.price} {item.currency}")
        print(f"   Регион:  {item.region}")
        print(f"   Статус:  {item.availability}")
        print(f"   Продавец: {item.seller_name}")
        print(f"   URL:     {item.item_url[:50]}..." if item.item_url else "   URL: нет")