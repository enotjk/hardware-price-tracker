# Hardware Price Tracker

Отслеживает цены на GPU, CPU, RAM с Amazon, eBay, Newegg.
США + Европа. ETL на Airflow, данные в PostgreSQL, дашборд на Next.js.

## Стек
- ETL: Python, Apache Airflow, dbt
- API: FastAPI
- DB: PostgreSQL (Supabase)
- Frontend: Next.js 14, Tailwind, Recharts
- Deploy: Railway (ETL+API), Vercel (Frontend)

## Локальный запуск
cp .env.example .env   # заполни значения
docker-compose up      # запустит всё