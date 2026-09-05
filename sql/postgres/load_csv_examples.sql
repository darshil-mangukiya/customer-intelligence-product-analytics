-- Example local loading commands after running the Python pipeline.
-- Adjust absolute paths for your machine, or use docker-compose volume paths.

\copy marts.dim_customer FROM 'data/marts/dim_customer.csv' WITH (FORMAT csv, HEADER true);
\copy marts.dim_product FROM 'data/marts/dim_product.csv' WITH (FORMAT csv, HEADER true);
\copy marts.dim_date FROM 'data/marts/dim_date.csv' WITH (FORMAT csv, HEADER true);
\copy marts.fact_orders FROM 'data/marts/fact_orders.csv' WITH (FORMAT csv, HEADER true);
\copy marts.fact_sessions FROM 'data/marts/fact_sessions.csv' WITH (FORMAT csv, HEADER true);
\copy marts.fact_customer_value FROM 'data/marts/fact_customer_value.csv' WITH (FORMAT csv, HEADER true);
\copy marts.fact_cohort_retention FROM 'data/marts/fact_cohort_retention.csv' WITH (FORMAT csv, HEADER true);

