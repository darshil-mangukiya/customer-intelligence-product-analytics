select *
from {{ ref('stg_orders') }}
where is_completed_order = true
  and net_revenue < 0

