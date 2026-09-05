with customers as (
    select customer_id from {{ ref('stg_customers') }}
),
customer_mart as (
    select customer_id from {{ ref('mart_customer_360') }}
)
select
    count(*) as customers,
    sum(case when m.customer_id is null then 1 else 0 end) as customers_missing_from_mart,
    1 - {{ safe_divide('sum(case when m.customer_id is null then 1 else 0 end)', 'count(*)') }} as scoring_coverage_rate
from customers c
left join customer_mart m
    on c.customer_id = m.customer_id

