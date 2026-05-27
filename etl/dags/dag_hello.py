"""
DAG: dag_hello
Тестовый DAG — проверяем что Airflow работает корректно.
Просто печатает сообщения и проверяет подключение к БД.
После проверки можно удалить этот файл.
"""
 
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
import logging
 
log = logging.getLogger(__name__)
 
# ─────────────────────────────────────────
# Настройки DAG по умолчанию
# ─────────────────────────────────────────
default_args = {
    "owner": "hardware-tracker",
    "retries": 1,                           # повторить 1 раз при ошибке
    "retry_delay": timedelta(minutes=5),    # ждать 5 минут перед повтором
    "email_on_failure": False,
}
 
# ─────────────────────────────────────────
# Определение DAG
# ─────────────────────────────────────────
with DAG(
    dag_id="dag_hello",                     # уникальное имя DAG
    description="Тестовый DAG для проверки Airflow",
    default_args=default_args,
    start_date=datetime(2024, 1, 1),
    schedule_interval=None,                 # None = запускаем только вручную
    catchup=False,                          # не запускать пропущенные запуски
    tags=["test"],
) as dag:
 
    # ─────────────────────────────────────
    # Task 1: просто печатает Hello
    # ─────────────────────────────────────
    def task_hello():
        log.info("=" * 50)
        log.info("Hello from Airflow!")
        log.info("DAG работает корректно")
        log.info("=" * 50)
 
    # ─────────────────────────────────────
    # Task 2: проверяет переменные окружения
    # ─────────────────────────────────────
    def task_check_env():
        import os
        db_url = os.getenv("DATABASE_URL", "НЕ ЗАДАН")
 
        # Не печатаем пароль — только проверяем что переменная существует
        if db_url == "НЕ ЗАДАН":
            log.warning("DATABASE_URL не задан в environment variables!")
        else:
            log.info("DATABASE_URL найден ✓")
            # Показываем только хост без пароля
            host = db_url.split("@")[-1] if "@" in db_url else "unknown"
            log.info(f"Database host: {host}")
 
    # ─────────────────────────────────────
    # Task 3: проверяет подключение к БД
    # ─────────────────────────────────────
    def task_check_db():
        import os
        import psycopg2
 
        db_url = os.getenv("DATABASE_URL")
 
        if not db_url:
            log.error("DATABASE_URL не задан — пропускаем проверку БД")
            return
 
        try:
            conn = psycopg2.connect(db_url)
            cursor = conn.cursor()
 
            # Проверяем что наши таблицы существуют
            cursor.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name;
            """)
            tables = [row[0] for row in cursor.fetchall()]
 
            log.info(f"Подключение к БД успешно ✓")
            log.info(f"Найдено таблиц: {len(tables)}")
            for table in tables:
                log.info(f"  • {table}")
 
            cursor.close()
            conn.close()
 
        except Exception as e:
            log.error(f"Ошибка подключения к БД: {e}")
            raise  # пробрасываем ошибку чтобы Task стал красным в UI
 
    # ─────────────────────────────────────
    # Task 4: финальное сообщение
    # ─────────────────────────────────────
    def task_done():
        log.info("=" * 50)
        log.info("Все проверки пройдены!")
        log.info("Airflow готов к работе")
        log.info("Следующий шаг: ETL-02 — eBay API клиент")
        log.info("=" * 50)
 
    # ─────────────────────────────────────
    # Создаём задачи
    # ─────────────────────────────────────
    t1 = PythonOperator(task_id="hello",        python_callable=task_hello)
    t2 = PythonOperator(task_id="check_env",    python_callable=task_check_env)
    t3 = PythonOperator(task_id="check_db",     python_callable=task_check_db)
    t4 = PythonOperator(task_id="done",         python_callable=task_done)
 
    # ─────────────────────────────────────
    # Порядок выполнения
    # ─────────────────────────────────────
    t1 >> t2 >> t3 >> t4
    # читается как: t1 запускается первым, потом t2, потом t3, потом t4
 