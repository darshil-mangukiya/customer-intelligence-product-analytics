with source as (
    select * from {{ source('raw', 'products') }}
),
deduped as (
    select
        *,
        row_number() over (partition by product_id order by launch_date desc) as row_num
    from source
)
select
    product_id,
    sku,
    product_name,
    initcap(category) as category,
    initcap(sub_category) as sub_category,
    base_price,
    unit_cost,
    margin_rate,
    lifecycle_stage,
    profitability_profile,
    return_profile,
    retention_profile,
    launch_date
from deduped
where row_num = 1

