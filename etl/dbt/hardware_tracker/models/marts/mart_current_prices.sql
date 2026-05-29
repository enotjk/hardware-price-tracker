with latest as (
    select
        product_id,
        source_id,
        price_usd,
        date_id,
        collected_at,
        row_number() over (
            partition by product_id, source_id
            order by collected_at desc
        ) as rn
    from {{ source('public', 'fact_price_history') }}
),

final as (
    select
        l.product_id,
        l.source_id,
        l.price_usd,
        l.date_id,
        l.collected_at,
        dp.name     as product_name,
        dp.brand,
        dp.category,
        ds.name     as source_name,
        ds.region
    from latest l
    left join {{ source('public', 'dim_products') }} dp on l.product_id = dp.product_id
    left join {{ source('public', 'dim_sources') }} ds  on l.source_id  = ds.source_id
    where l.rn = 1
)

select * from final