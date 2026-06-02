"""
Pipelines router — эндпоинты для ETL мониторинга
"""

from fastapi import APIRouter
from database import execute_query
from schemas import PipelineSchema, StatsSchema

router = APIRouter(prefix="/pipelines", tags=["Pipelines"])


@router.get("", response_model=list[PipelineSchema])
async def get_pipelines():
    sql = """
        SELECT DISTINCT ON (dag_id)
            dag_id,
            status,
            started_at,
            finished_at,
            records_fetched,
            records_inserted,
            error_message,
            api_requests_used
        FROM etl_runs
        ORDER BY dag_id, started_at DESC
    """
    return execute_query(sql)


@router.get("/stats", response_model=StatsSchema)
async def get_stats():
    sql = """
        SELECT
            (SELECT COUNT(*) FROM fact_price_history)::int                      AS total_price_records,
            (SELECT COUNT(*) FROM raw_prices)::int                              AS total_raw_records,
            (SELECT COUNT(*) FROM dim_products WHERE is_active = true)::int     AS tracked_products,
            (SELECT MAX(collected_at) FROM fact_price_history)                  AS last_collected_at,
            (SELECT COUNT(*) FROM etl_runs WHERE status = 'success')::int       AS successful_runs,
            (SELECT COUNT(*) FROM etl_runs WHERE status = 'failed')::int        AS failed_runs,
            (SELECT COALESCE(SUM(api_requests_used), 0)
             FROM etl_runs
             WHERE dag_id = 'dag_amazon'
               AND started_at >= date_trunc('month', NOW()))::int               AS amazon_requests_this_month
    """
    rows = execute_query(sql)
    return rows[0] if rows else {}


@router.get("/{dag_id}/runs", response_model=list[PipelineSchema])
async def get_dag_runs(dag_id: str, limit: int = 10):
    sql = """
        SELECT
            dag_id,
            status,
            started_at,
            finished_at,
            records_fetched,
            records_inserted,
            error_message,
            api_requests_used
        FROM etl_runs
        WHERE dag_id = %s
        ORDER BY started_at DESC
        LIMIT %s
    """
    return execute_query(sql, (dag_id, limit))