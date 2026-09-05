{% snapshot customer_value_snapshot %}

{{
    config(
      target_schema='snapshots',
      unique_key='customer_id',
      strategy='check',
      check_cols=['orders', 'net_revenue', 'return_adjusted_profit', 'recency_days', 'repeat_purchase_flag']
    )
}}

select
    customer_id,
    orders,
    net_revenue,
    return_adjusted_profit,
    recency_days,
    repeat_purchase_flag
from {{ ref('mart_customer_360') }}

{% endsnapshot %}

