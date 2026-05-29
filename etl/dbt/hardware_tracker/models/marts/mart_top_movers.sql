-- models/marts/mart_top_movers.sql
with changes as (
    select * from {{ ref('mart_price_changes') }}
    where change_7d_pct is not null
),

top_gainers as (
    select *, 'gainer' as mover_type
    from changes
    order by change_7d_pct desc
    limit 10
),

top_losers as (
    select *, 'loser' as mover_type
    from changes
    order by change_7d_pct asc
    limit 10
)

select * from top_gainers
union all
select * from top_losers