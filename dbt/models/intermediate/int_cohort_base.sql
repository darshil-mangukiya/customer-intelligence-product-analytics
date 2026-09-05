with orders as (
    select
        o.customer_id,
        o.order_id,
        o.order_date,
        date_trunc('month', o.order_date)::date as order_month,
        o.net_revenue,
        o.return_adjusted_profit,
        c.acquisition_channel,
        p.category
    from {{ ref('stg_orders') }} o
    left join {{ ref('stg_customers') }} c on o.customer_id = c.customer_id
    left join {{ ref('stg_products') }} p on o.product_id = p.product_id
),
first_orders as (
    select
        customer_id,
        min(order_date) as first_order_date,
        date_trunc('month', min(order_date))::date as cohort_month
    from orders
    group by customer_id
)
select
    o.*,
    f.cohort_month,
    ((extract(year from o.order_month) - extract(year from f.cohort_month)) * 12
      + extract(month from o.order_month) - extract(month from f.cohort_month))::int as cohort_index
from orders o
join first_orders f on o.customer_id = f.customer_id

