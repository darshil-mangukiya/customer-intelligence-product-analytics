with product_profitability as (
    select * from {{ ref('int_product_profitability') }}
),
thresholds as (
    select
        percentile_cont(0.75) within group (order by orders) as high_volume_threshold,
        percentile_cont(0.35) within group (order by return_adjusted_margin) as low_margin_threshold,
        percentile_cont(0.90) within group (order by return_rate) as return_heavy_threshold
    from product_profitability
)
select
    product_profitability.*,
    case
        when orders >= high_volume_threshold
         and return_adjusted_margin < low_margin_threshold
            then 'Low Margin High Volume'
        when return_rate >= return_heavy_threshold
            then 'Return Heavy'
        else 'Stable'
    end as product_performance_flag
from product_profitability
cross join thresholds
