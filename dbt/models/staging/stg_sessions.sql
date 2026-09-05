with source as (
    select * from {{ source('raw', 'web_behavior') }}
),
deduped as (
    select
        *,
        row_number() over (partition by session_id order by session_date desc) as row_num
    from source
)
select
    session_id,
    customer_id,
    session_date,
    least(greatest(page_views, 1), 120) as page_views,
    least(greatest(time_spent, 0), 7200) as time_spent,
    coalesce(bounce_flag, false) as bounce_flag,
    initcap(coalesce(device_type, 'Unknown')) as device_type,
    case
        when trim(lower(traffic_source)) = 'paid_social' then 'Paid Social'
        when trim(lower(traffic_source)) = 'organic' then 'Organic Search'
        when trim(traffic_source) = '' or traffic_source is null then 'Unknown'
        else initcap(trim(traffic_source))
    end as traffic_source
from deduped
where row_num = 1

