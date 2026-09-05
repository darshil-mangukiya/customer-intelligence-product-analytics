CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS marts;
CREATE SCHEMA IF NOT EXISTS audit;

CREATE TABLE IF NOT EXISTS raw.customers (
    customer_id TEXT,
    signup_date DATE,
    age INTEGER,
    gender TEXT,
    income_band TEXT,
    acquisition_channel TEXT,
    region_id TEXT,
    state TEXT,
    city TEXT,
    loyalty_tier TEXT,
    segment_seed TEXT,
    preferred_category TEXT,
    discount_sensitivity NUMERIC,
    return_propensity NUMERIC,
    churn_status TEXT,
    tenure_days INTEGER,
    repeat_purchase_behavior TEXT
);

CREATE TABLE IF NOT EXISTS raw.products (
    product_id TEXT,
    sku TEXT,
    product_name TEXT,
    category TEXT,
    sub_category TEXT,
    base_price NUMERIC,
    unit_cost NUMERIC,
    margin_rate NUMERIC,
    lifecycle_stage TEXT,
    profitability_profile TEXT,
    return_profile TEXT,
    retention_profile TEXT,
    launch_date DATE
);

CREATE TABLE IF NOT EXISTS raw.transactions (
    order_id TEXT,
    customer_id TEXT,
    product_id TEXT,
    order_date DATE,
    quantity INTEGER,
    revenue NUMERIC,
    discount NUMERIC,
    return_flag BOOLEAN,
    cost NUMERIC,
    profit NUMERIC,
    region_id TEXT,
    sales_channel TEXT,
    order_status TEXT
);

CREATE TABLE IF NOT EXISTS raw.web_behavior (
    session_id TEXT,
    customer_id TEXT,
    session_date DATE,
    page_views INTEGER,
    time_spent NUMERIC,
    bounce_flag BOOLEAN,
    device_type TEXT,
    traffic_source TEXT
);

CREATE TABLE IF NOT EXISTS raw.engagement (
    customer_id TEXT,
    email_opens INTEGER,
    clicks INTEGER,
    campaign_interactions INTEGER,
    last_engagement_date DATE,
    engagement_score NUMERIC
);

CREATE TABLE IF NOT EXISTS audit.data_quality_summary (
    table_name TEXT,
    raw_rows BIGINT,
    clean_rows BIGINT,
    duplicate_rows_removed BIGINT,
    rejected_or_flagged_rows BIGINT,
    raw_null_cells BIGINT,
    clean_null_cells BIGINT,
    loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS marts.dim_customer (
    customer_id TEXT PRIMARY KEY,
    signup_date DATE,
    age INTEGER,
    gender TEXT,
    income_band TEXT,
    acquisition_channel TEXT,
    region_id TEXT,
    state TEXT,
    city TEXT,
    loyalty_tier TEXT,
    segment_seed TEXT,
    preferred_category TEXT,
    churn_status TEXT
);

CREATE TABLE IF NOT EXISTS marts.dim_product (
    product_id TEXT PRIMARY KEY,
    sku TEXT,
    product_name TEXT,
    category TEXT,
    sub_category TEXT,
    base_price NUMERIC,
    unit_cost NUMERIC,
    margin_rate NUMERIC,
    lifecycle_stage TEXT,
    profitability_profile TEXT,
    return_profile TEXT,
    retention_profile TEXT,
    launch_date DATE
);

CREATE TABLE IF NOT EXISTS marts.dim_date (
    date_key INTEGER PRIMARY KEY,
    date DATE,
    year INTEGER,
    quarter TEXT,
    month INTEGER,
    month_name TEXT,
    week INTEGER,
    day_of_week TEXT,
    is_weekend BOOLEAN
);

CREATE TABLE IF NOT EXISTS marts.fact_orders (
    order_id TEXT PRIMARY KEY,
    customer_id TEXT REFERENCES marts.dim_customer(customer_id),
    product_id TEXT REFERENCES marts.dim_product(product_id),
    date_key INTEGER REFERENCES marts.dim_date(date_key),
    order_date DATE,
    quantity INTEGER,
    gross_revenue NUMERIC,
    net_revenue NUMERIC,
    discount_amount NUMERIC,
    return_loss NUMERIC,
    cost NUMERIC,
    return_adjusted_profit NUMERIC,
    return_flag BOOLEAN,
    region_id TEXT,
    sales_channel TEXT,
    order_status TEXT,
    is_completed_order BOOLEAN
);

CREATE TABLE IF NOT EXISTS marts.fact_sessions (
    session_id TEXT PRIMARY KEY,
    customer_id TEXT REFERENCES marts.dim_customer(customer_id),
    date_key INTEGER REFERENCES marts.dim_date(date_key),
    session_date DATE,
    page_views INTEGER,
    time_spent NUMERIC,
    bounce_flag BOOLEAN,
    device_type TEXT,
    traffic_source TEXT,
    odd_session_flag BOOLEAN
);

CREATE TABLE IF NOT EXISTS marts.fact_customer_value (
    customer_id TEXT PRIMARY KEY REFERENCES marts.dim_customer(customer_id),
    orders INTEGER,
    net_revenue NUMERIC,
    return_adjusted_profit NUMERIC,
    historical_clv NUMERIC,
    customer_value_band TEXT,
    recency_days INTEGER,
    purchase_frequency_30d NUMERIC,
    repeat_purchase_flag INTEGER,
    churn_label INTEGER
);

CREATE TABLE IF NOT EXISTS marts.fact_cohort_retention (
    cohort_month TEXT,
    cohort_index INTEGER,
    customers INTEGER,
    net_revenue NUMERIC,
    profit NUMERIC,
    cohort_customers INTEGER,
    retention_rate NUMERIC
);

CREATE INDEX IF NOT EXISTS idx_fact_orders_customer ON marts.fact_orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_fact_orders_product ON marts.fact_orders(product_id);
CREATE INDEX IF NOT EXISTS idx_fact_orders_date ON marts.fact_orders(date_key);
CREATE INDEX IF NOT EXISTS idx_fact_sessions_customer ON marts.fact_sessions(customer_id);

