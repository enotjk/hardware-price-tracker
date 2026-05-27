from dotenv import load_dotenv
load_dotenv()

import psycopg2, os, logging
from normalizer import Normalizer
from deduplicator import Deduplicator
from dataclasses import dataclass
from typing import Optional

logging.basicConfig(level=logging.INFO)

# Тестовые листинги (имитируем ответ eBay)
@dataclass
class FakeListing:
    title: str
    price: float
    currency: str
    region: str
    availability: str = "IN_STOCK"
    seller_name: Optional[str] = "test_seller"
    item_url: Optional[str] = "https://ebay.com/test"

fake_listings = [
    FakeListing("ASUS ROG STRIX GeForce RTX 4090 OC 24GB GDDR6X Gaming", 1749.99, "USD", "US"),
    FakeListing("MSI GeForce RTX 4090 SUPRIM X 24G Graphics Card", 1829.00, "USD", "US"),
    FakeListing("Gigabyte AMD Radeon RX 7900 XTX Gaming OC 24GB", 899.00, "USD", "US"),
    FakeListing("EVGA GeForce RTX 4090 FTW3 ULTRA GAMING 24GB", 1799.99, "USD", "US"),  # дубль RTX 4090
    FakeListing("Some Random Unknown GPU 8GB", 299.00, "USD", "US"),  # не найдётся
]

# Загружаем продукты из БД
db_url = os.getenv("DIRECT_URL")
conn = psycopg2.connect(db_url)
cursor = conn.cursor()
cursor.execute("SELECT product_id, name, model_number, brand, category FROM dim_products")
cols = [d[0] for d in cursor.description]
products = [dict(zip(cols, row)) for row in cursor.fetchall()]
cursor.close()

print(f"\nЗагружено {len(products)} продуктов из dim_products")

# Инициализируем трансформер
import exchange_rates
exchange = exchange_rates.ExchangeRateClient()
normalizer = Normalizer(products, exchange)
deduplicator = Deduplicator()

# Нормализуем
from datetime import date
normalized, skipped = normalizer.normalize_batch(
    fake_listings,
    source_id=1,
    date_id=str(date.today()),
    etl_run_id="test_run_001"
)

print(f"\n=== Результат нормализации ===")
print(f"Успешно: {len(normalized)}, Пропущено: {skipped}")
for r in normalized:
    print(f"  • {r.listing_title[:50]}...")
    print(f"    Цена: {r.price_usd} USD | product_id: {r.product_id[:8]}...")

# Дедупликация
unique = deduplicator.deduplicate(normalized)
print(f"\n=== После дедупликации ===")
print(f"Уникальных записей: {len(unique)}")

conn.close()