select
    sum(net_revenue) as total_net_revenue,
    sum(return_adjusted_profit) as total_return_adjusted_profit,
    sum(return_loss + discount_amount) as revenue_leakage,
    {{ safe_divide('sum(return_adjusted_profit)', 'sum(net_revenue)') }} as return_adjusted_margin,
    count(distinct order_id) as total_orders,
    count(distinct customer_id) as purchasing_customers,
    {{ safe_divide('sum(case when return_flag then 1 else 0 end)', 'count(distinct order_id)') }} as return_rate
from {{ ref('stg_orders') }}

