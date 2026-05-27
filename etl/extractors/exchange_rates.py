"""
ExchangeRate API клиент
Документация: https://www.exchangerate-api.com/docs/overview
 
Что делает:
- Получает актуальный курс валют (EUR/GBP → USD)
- Кеширует курс в памяти на 1 час (не тратим запросы)
- Сохраняет дневной курс в таблицу exchange_rates в БД
"""
 
import os
import time
import logging
import requests
from datetime import date, datetime
from typing import Optional
 
log = logging.getLogger(__name__)
 
 
class ExchangeRateClient:
    """
    Клиент для ExchangeRate API.
 
    Использование:
        client = ExchangeRateClient()
        rate = client.get_rate("EUR", "USD")   # например 1.085
        usd = client.convert(100, "EUR")        # 108.5
    """
 
    BASE_URL = "https://v6.exchangerate-api.com/v6"
 
    def __init__(self):
        self.api_key = os.getenv("EXCHANGE_RATE_API_KEY")
 
        if not self.api_key:
            raise ValueError(
                "EXCHANGE_RATE_API_KEY должен быть задан в .env"
            )
 
        # Кеш курсов — { "EUR": 1.085, "GBP": 1.27 }
        self._rates_cache: dict = {}
        self._cache_expires_at: float = 0
 
    # ─────────────────────────────────────
    # Получить все курсы относительно USD
    # ─────────────────────────────────────
    def _fetch_rates(self) -> dict:
        """
        Запрашивает все курсы валют относительно USD.
        Кеширует результат на 1 час.
        """
        # Если кеш ещё свежий — возвращаем его
        if self._rates_cache and time.time() < self._cache_expires_at:
            log.debug("Курсы из кеша")
            return self._rates_cache
 
        log.info("Запрашиваем актуальные курсы валют...")
 
        url = f"{self.BASE_URL}/{self.api_key}/latest/USD"
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()
 
        if data.get("result") != "success":
            raise ValueError(f"ExchangeRate API вернул ошибку: {data.get('error-type')}")
 
        # Курсы приходят как USD → X, нам нужно X → USD
        # Поэтому инвертируем: если 1 USD = 0.92 EUR, то 1 EUR = 1/0.92 USD
        raw_rates = data.get("conversion_rates", {})
        inverted = {
            currency: round(1 / rate, 6)
            for currency, rate in raw_rates.items()
            if rate > 0
        }
 
        self._rates_cache = inverted
        self._cache_expires_at = time.time() + 3600  # кеш на 1 час
 
        log.info(f"Курсы обновлены. EUR/USD: {inverted.get('EUR', 'н/д')}")
        return inverted
 
    # ─────────────────────────────────────
    # Публичные методы
    # ─────────────────────────────────────
    def get_rate(self, from_currency: str, to_currency: str = "USD") -> float:
        """
        Возвращает курс конвертации.
 
        Args:
            from_currency: из какой валюты ('EUR', 'GBP')
            to_currency:   в какую валюту (всегда 'USD')
 
        Returns:
            float: курс, например 1.085 означает 1 EUR = 1.085 USD
        """
        if from_currency == to_currency:
            return 1.0
 
        if to_currency != "USD":
            raise ValueError("Конвертация поддерживается только в USD")
 
        rates = self._fetch_rates()
        rate = rates.get(from_currency)
 
        if not rate:
            raise ValueError(f"Курс для {from_currency} не найден")
 
        return rate
 
    def convert(self, amount: float, from_currency: str, to_currency: str = "USD") -> float:
        """
        Конвертирует сумму из одной валюты в другую.
 
        Args:
            amount:        сумма для конвертации
            from_currency: исходная валюта ('EUR', 'GBP')
            to_currency:   целевая валюта (всегда 'USD')
 
        Returns:
            float: сумма в USD, округлённая до 2 знаков
        """
        rate = self.get_rate(from_currency, to_currency)
        result = round(amount * rate, 2)
        log.debug(f"{amount} {from_currency} = {result} {to_currency} (курс {rate})")
        return result
 
    def get_all_rates(self) -> dict:
        """
        Возвращает все актуальные курсы к USD.
        Нужно для сохранения в БД.
        """
        return self._fetch_rates()
 
    # ─────────────────────────────────────
    # Сохранение курса в БД
    # ─────────────────────────────────────
    def save_rates_to_db(self, conn) -> None:
        """
        Сохраняет дневные курсы EUR и GBP в таблицу exchange_rates.
        Вызывается из Airflow DAG один раз в день.
 
        Args:
            conn: psycopg2 подключение к БД
        """
        rates = self._fetch_rates()
        today = date.today()
        currencies = ["EUR", "GBP"]  # валюты которые нам нужны
 
        cursor = conn.cursor()
 
        for currency in currencies:
            rate = rates.get(currency)
            if not rate:
                log.warning(f"Курс {currency} не найден, пропускаем")
                continue
 
            # INSERT OR UPDATE — если запись на сегодня уже есть, обновляем
            cursor.execute("""
                INSERT INTO exchange_rates (date, from_currency, to_currency, rate)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (date, from_currency, to_currency)
                DO UPDATE SET rate = EXCLUDED.rate
            """, (today, currency, "USD", rate))
 
            log.info(f"Сохранён курс: 1 {currency} = {rate} USD на {today}")
 
        conn.commit()
        cursor.close()
        log.info("Курсы валют сохранены в БД")
 
 
# ─────────────────────────────────────────
# Быстрый тест — запускай напрямую:
# python etl/extractors/exchange_rates.py
# ─────────────────────────────────────────
if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
 
    logging.basicConfig(level=logging.INFO)
 
    client = ExchangeRateClient()
 
    print("\n=== Тест: курсы валют ===")
    eur_rate = client.get_rate("EUR")
    gbp_rate = client.get_rate("GBP")
    print(f"1 EUR = {eur_rate} USD")
    print(f"1 GBP = {gbp_rate} USD")
 
    print("\n=== Тест: конвертация ===")
    amounts = [100, 500, 1000, 1899]
    for amount in amounts:
        usd = client.convert(amount, "EUR")
        print(f"  {amount} EUR = {usd} USD")    
