select
    date_trunc('month', order_date)::date as month,
    count(distinct order_id) as orders,
    count(distinct customer_id) as purchasing_customers,
    sum(net_revenue) as net_revenue,
    sum(return_adjusted_profit) as return_adjusted_profit,
    {{ safe_divide('sum(return_adjusted_profit)', 'sum(net_revenue)') }} as return_adjusted_margin,
    {{ safe_divide('sum(case when return_flag then 1 else 0 end)', 'count(distinct order_id)') }} as return_rate
from {{ ref('stg_orders') }}
group by 1
order by 1

