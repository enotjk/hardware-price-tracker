with current_price as (
    select product_id, source_id, price_usd, collected_at,
        row_number() over (partition by product_id, source_id order by collected_at desc) as rn
    from {{ source('public', 'fact_price_history') }}
),

price_1d as (
    select product_id, source_id, avg(price_usd) as price_usd
    from {{ source('public', 'fact_price_history') }}
    where collected_at >= now() - interval '1 day'
    group by product_id, source_id
),

price_7d as (
    select product_id, source_id, avg(price_usd) as price_usd
    from {{ source('public', 'fact_price_history') }}
    where collected_at >= now() - interval '7 days'
      and collected_at < now() - interval '1 day'
    group by product_id, source_id
),

price_30d as (
    select product_id, source_id, avg(price_usd) as price_usd
    from {{ source('public', 'fact_price_history') }}
    where collected_at >= now() - interval '30 days'
      and collected_at < now() - interval '7 days'
    group by product_id, source_id
),

final as (
    select
        c.product_id,
        c.source_id,
        c.price_usd                                               as current_price,
        p1.price_usd                                              as price_1d_ago,
        p7.price_usd                                              as price_7d_ago,
        p30.price_usd                                             as price_30d_ago,
        round((c.price_usd - p1.price_usd)  / nullif(p1.price_usd,  0) * 100, 2) as change_1d_pct,
        round((c.price_usd - p7.price_usd)  / nullif(p7.price_usd,  0) * 100, 2) as change_7d_pct,
        round((c.price_usd - p30.price_usd) / nullif(p30.price_usd, 0) * 100, 2) as change_30d_pct,
        dp.name     as product_name,
        dp.category,
        ds.region
    from current_price c
    left join price_1d  p1  on c.product_id = p1.product_id  and c.source_id = p1.source_id
    left join price_7d  p7  on c.product_id = p7.product_id  and c.source_id = p7.source_id
    left join price_30d p30 on c.product_id = p30.product_id and c.source_id = p30.source_id
    left join {{ source('public', 'dim_products') }} dp on c.product_id = dp.product_id
    left join {{ source('public', 'dim_sources') }}  ds on c.source_id  = ds.source_id
    where c.rn = 1
)

select * from final