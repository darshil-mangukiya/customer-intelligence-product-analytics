with cohort as (
    select * from {{ ref('int_cohort_base') }}
    where cohort_index between 0 and 12
),
retention as (
    select
        cohort_month,
        cohort_index,
        count(distinct customer_id) as active_customers,
        count(distinct order_id) as orders,
        sum(net_revenue) as net_revenue,
        sum(return_adjusted_profit) as profit
    from cohort
    group by cohort_month, cohort_index
),
base as (
    select
        cohort_month,
        active_customers as cohort_size,
        net_revenue as month_0_revenue
    from retention
    where cohort_index = 0
)
select
    r.*,
    b.cohort_size,
    {{ safe_divide('r.active_customers', 'b.cohort_size') }} as retention_rate,
    {{ safe_divide('r.net_revenue', 'b.month_0_revenue') }} as revenue_retention_rate
from retention r
join base b on r.cohort_month = b.cohort_month

