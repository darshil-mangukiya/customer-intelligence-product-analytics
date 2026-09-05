with customers as (
    select * from {{ ref('stg_customers') }}
),
features as (
    select * from {{ ref('int_customer_order_features') }}
),
engagement as (
    select * from {{ ref('stg_engagement') }}
)
select
    c.customer_id,
    c.signup_date,
    c.acquisition_channel,
    c.region_id,
    c.loyalty_tier,
    c.segment_seed,
    c.preferred_category,
    coalesce(f.orders, 0) as orders,
    coalesce(f.net_revenue, 0) as net_revenue,
    coalesce(f.return_adjusted_profit, 0) as return_adjusted_profit,
    coalesce(f.avg_order_value, 0) as avg_order_value,
    coalesce(f.discount_amount, 0) as discount_amount,
    coalesce(
        {{ safe_divide('coalesce(f.returns, 0)', 'coalesce(f.orders, 0)') }},
        0
    ) as return_rate,
    coalesce(e.engagement_score, 0) as engagement_score,
    coalesce(e.engagement_rate, 0) as engagement_rate,
    case
        when f.last_order_date is null then 999
        else current_date - f.last_order_date
    end as recency_days,
    case
        when coalesce(f.orders, 0) >= 2 then 1
        else 0
    end as repeat_purchase_flag
from customers c
left join features f on c.customer_id = f.customer_id
left join engagement e on c.customer_id = e.customer_id
