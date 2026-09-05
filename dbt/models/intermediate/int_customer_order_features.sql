with orders as (
    select * from {{ ref('stg_orders') }}
),
products as (
    select product_id, category from {{ ref('stg_products') }}
)
select
    o.customer_id,
    count(distinct o.order_id) as orders,
    sum(case when o.is_completed_order then 1 else 0 end) as completed_orders,
    sum(o.quantity) as units,
    sum(o.gross_revenue) as gross_revenue,
    sum(o.net_revenue) as net_revenue,
    sum(o.return_adjusted_profit) as return_adjusted_profit,
    sum(o.discount_amount) as discount_amount,
    sum(case when o.return_flag then 1 else 0 end) as returns,
    min(o.order_date) as first_order_date,
    max(o.order_date) as last_order_date,
    avg(o.net_revenue) as avg_order_value,
    avg(o.discount_rate) as avg_discount_rate,
    count(distinct p.category) as category_diversity,
    count(distinct o.product_id) as product_diversity,
    count(distinct o.sales_channel) as channel_diversity
from orders o
left join products p on o.product_id = p.product_id
group by o.customer_id

