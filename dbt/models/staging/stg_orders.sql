with source as (
    select * from {{ source('raw', 'transactions') }}
),
deduped as (
    select
        *,
        row_number() over (partition by order_id order by order_date desc) as row_num
    from source
),
standardized as (
    select
        order_id,
        customer_id,
        product_id,
        order_date,
        greatest(quantity, 1) as quantity,
        greatest(revenue, 0) as gross_revenue,
        least(greatest(coalesce(discount, 0), 0), 0.85) as discount_rate,
        coalesce(return_flag, false) as return_flag,
        greatest(cost, 0) as cost,
        profit,
        region_id,
        case
            when trim(lower(sales_channel)) = 'web' then 'Web'
            when trim(lower(sales_channel)) = 'mobile_app' then 'Mobile App'
            when trim(lower(sales_channel)) = 'market place' then 'Marketplace'
            when trim(sales_channel) = '' or sales_channel is null then 'Unknown'
            else initcap(trim(sales_channel))
        end as sales_channel,
        initcap(order_status) as order_status
    from deduped
    where row_num = 1
)
select
    *,
    case when return_flag or order_status in ('Returned', 'Cancelled') then 0 else gross_revenue end as net_revenue,
    case
        when discount_rate > 0 then gross_revenue * discount_rate / nullif(1 - discount_rate, 0)
        else 0
    end as discount_amount,
    case when return_flag or order_status in ('Returned', 'Cancelled') then gross_revenue + cost * 0.15 else 0 end as return_loss,
    case when return_flag or order_status in ('Returned', 'Cancelled') then -cost * 0.15 else profit end as return_adjusted_profit,
    order_status = 'Completed' as is_completed_order
from standardized

