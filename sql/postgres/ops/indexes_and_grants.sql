CREATE INDEX IF NOT EXISTS idx_marts_churn_risk_tier
    ON marts.mart_churn_risk (churn_risk_tier);

CREATE INDEX IF NOT EXISTS idx_marts_churn_customer
    ON marts.mart_churn_risk (customer_id);

CREATE INDEX IF NOT EXISTS idx_marts_clv_band
    ON marts.mart_clv (clv_band);

CREATE INDEX IF NOT EXISTS idx_marts_clv_customer
    ON marts.mart_clv (customer_id);

CREATE INDEX IF NOT EXISTS idx_marts_segments_name
    ON marts.mart_customer_segments (segment_name);

CREATE INDEX IF NOT EXISTS idx_marts_product_category
    ON marts.mart_product_profitability (category);

CREATE INDEX IF NOT EXISTS idx_marts_orders_date_customer
    ON marts.fact_orders (date_key, customer_id);

-- Example BI read-only grant pattern.
-- CREATE ROLE bi_reader;
-- GRANT USAGE ON SCHEMA marts TO bi_reader;
-- GRANT SELECT ON ALL TABLES IN SCHEMA marts TO bi_reader;
-- ALTER DEFAULT PRIVILEGES IN SCHEMA marts GRANT SELECT ON TABLES TO bi_reader;

