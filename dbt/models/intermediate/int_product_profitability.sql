with orders as (
    select * from {{ ref('stg_orders') }}
),
products as (
    select * from {{ ref('stg_products') }}
)
select
    p.product_id,
    p.product_name,
    p.category,
    p.sub_category,
    p.lifecycle_stage,
    count(distinct o.order_id) as orders,
    sum(o.quantity) as units,
    count(distinct o.customer_id) as customers,
    sum(o.net_revenue) as net_revenue,
    sum(o.return_adjusted_profit) as return_adjusted_profit,
    sum(o.discount_amount) as discount_amount,
    {{ safe_divide('sum(case when o.return_flag then 1 else 0 end)', 'count(distinct o.order_id)') }} as return_rate,
    {{ safe_divide('sum(o.return_adjusted_profit)', 'sum(o.net_revenue)') }} as return_adjusted_margin
from products p
left join orders o on p.product_id = o.product_id
group by
    p.product_id,
    p.product_name,
    p.category,
    p.sub_category,
    p.lifecycle_stage

