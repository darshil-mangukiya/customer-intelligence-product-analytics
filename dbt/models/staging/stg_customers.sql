with source as (
    select * from {{ source('raw', 'customers') }}
),
deduped as (
    select
        *,
        row_number() over (partition by customer_id order by signup_date desc) as row_num
    from source
)
select
    customer_id,
    signup_date,
    age,
    gender,
    income_band,
    case
        when trim(lower(acquisition_channel)) in ('paid_search', 'paid search') then 'Paid Search'
        when trim(lower(acquisition_channel)) in ('paid_social', 'paid social') then 'Paid Social'
        when trim(acquisition_channel) = '' or acquisition_channel is null then 'Unknown'
        else initcap(trim(acquisition_channel))
    end as acquisition_channel,
    region_id,
    state,
    city,
    coalesce(loyalty_tier, 'Base') as loyalty_tier,
    segment_seed,
    coalesce(nullif(preferred_category, ''), 'Unknown') as preferred_category,
    discount_sensitivity,
    return_propensity,
    churn_status,
    tenure_days,
    repeat_purchase_behavior
from deduped
where row_num = 1

