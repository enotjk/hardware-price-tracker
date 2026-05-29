"""
Pipelines router — эндпоинты для ETL мониторинга
"""

from fastapi import APIRouter
from database import execute_query

router = APIRouter(prefix="/pipelines", tags=["Pipelines"])


@router.get("")
async def get_pipelines():
    """Список DAGов с последним статусом"""
    sql = """
        SELECT DISTINCT ON (dag_id)
            dag_id,
            status,
            started_at,
            finished_at,
            records_fetched,
            records_inserted,
            error_message
        FROM etl_runs
        ORDER BY dag_id, started_at DESC
    """
    return execute_query(sql)


@router.get("/stats")
async def get_stats():
    """Общая статистика системы"""
    sql = """
        SELECT
            (SELECT COUNT(*) FROM fact_price_history)  as total_price_records,
            (SELECT COUNT(*) FROM raw_prices)           as total_raw_records,
            (SELECT COUNT(*) FROM dim_products WHERE is_active = true) as tracked_products,
            (SELECT MAX(collected_at) FROM fact_price_history) as last_collected_at,
            (SELECT COUNT(*) FROM etl_runs WHERE status = 'success') as successful_runs,
            (SELECT COUNT(*) FROM etl_runs WHERE status = 'failed')  as failed_runs
    """
    rows = execute_query(sql)
    return rows[0] if rows else {}


@router.get("/{dag_id}/runs")
async def get_dag_runs(dag_id: str, limit: int = 10):
    """История запусков конкретного DAG"""
    sql = """
        SELECT
            id, dag_id, status,
            started_at, finished_at,
            records_fetched, records_inserted,
            error_message
        FROM etl_runs
        WHERE dag_id = %s
        ORDER BY started_at DESC
        LIMIT %s
    """
    return execute_query(sql, (dag_id, limit))