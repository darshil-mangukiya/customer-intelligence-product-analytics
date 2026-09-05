select
    customer_id,
    coalesce(email_opens, 0) as email_opens,
    coalesce(clicks, 0) as clicks,
    coalesce(campaign_interactions, 0) as campaign_interactions,
    last_engagement_date,
    least(greatest(coalesce(engagement_score, 0), 0), 100) as engagement_score,
    {{ safe_divide('coalesce(clicks, 0)', 'nullif(coalesce(email_opens, 0), 0)') }} as engagement_rate
from {{ source('raw', 'engagement') }}

