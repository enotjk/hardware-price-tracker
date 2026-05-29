-- models/staging/stg_raw_prices.sql
with source as (
    select
        id,
        source_id,
        product_query,
        raw_json,
        fetched_at,
        etl_run_id
    from {{ source('public', 'raw_prices') }}
),

parsed as (
    select
        id,
        source_id,
        product_query,
        etl_run_id,
        fetched_at,
        json_array_elements(raw_json::json) as item
    from source
),

final as (
    select
        id,
        source_id,
        product_query,
        etl_run_id,
        fetched_at,
        (item->>'title')::text         as title,
        (item->>'price')::numeric      as price,
        (item->>'currency')::text      as currency,
        (item->>'url')::text           as url
    from parsed
    where (item->>'price') is not null
      and (item->>'price')::numeric > 0
)

select * from final