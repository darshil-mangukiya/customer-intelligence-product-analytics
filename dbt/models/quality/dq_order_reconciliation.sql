select
    count(distinct order_id) as orders,
    sum(net_revenue) as net_revenue,
    sum(return_adjusted_profit) as return_adjusted_profit,
    sum(return_loss + discount_amount) as revenue_leakage,
    sum(case when net_revenue < 0 then 1 else 0 end) as negative_net_revenue_orders
from {{ ref('stg_orders') }}

