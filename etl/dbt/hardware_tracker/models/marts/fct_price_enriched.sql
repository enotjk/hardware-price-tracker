select
    fph.id,
    fph.product_id,
    fph.source_id,
    fph.price_usd,
    fph.price_original,
    fph.currency,
    fph.date_id,
    fph.etl_run_id,
    fph.collected_at,
    dp.name        as product_name,
    dp.brand,
    dp.category,
    ds.name        as source_name,
    ds.region
from {{ source('public', 'fact_price_history') }} fph
left join {{ source('public', 'dim_products') }} dp on fph.product_id = dp.product_id
left join {{ source('public', 'dim_sources') }} ds  on fph.source_id  = ds.source_id