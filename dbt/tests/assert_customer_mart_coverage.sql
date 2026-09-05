select *
from {{ ref('dq_customer_scoring_coverage') }}
where scoring_coverage_rate < 0.99

