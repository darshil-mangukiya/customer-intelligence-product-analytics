select
    c.acquisition_channel,
    count(distinct c.customer_id) as customers,
    sum(o.net_revenue) as net_revenue,
    sum(o.return_adjusted_profit) as return_adjusted_profit,
    avg(case when cv.repeat_purchase_flag = 1 then 1.0 else 0.0 end) as repeat_purchase_rate
from {{ ref('stg_customers') }} c
left join {{ ref('stg_orders') }} o on c.customer_id = o.customer_id
left join {{ ref('mart_customer_360') }} cv on c.customer_id = cv.customer_id
group by 1
order by return_adjusted_profit desc

