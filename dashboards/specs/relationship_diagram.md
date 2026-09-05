# Power BI Relationship Diagram

```mermaid
erDiagram
    dim_customer ||--o{ fact_orders : customer_id
    dim_customer ||--o{ fact_sessions : customer_id
    dim_customer ||--|| fact_customer_value : customer_id
    dim_customer ||--|| mart_churn_risk : customer_id
    dim_customer ||--|| mart_clv : customer_id
    dim_customer ||--|| mart_customer_segments : customer_id
    dim_product ||--o{ fact_orders : product_id
    dim_date ||--o{ fact_orders : date_key
    dim_date ||--o{ fact_sessions : date_key
    dim_device ||--o{ fact_sessions : device_type
    dim_channel ||--o{ fact_orders : sales_channel
```

## Relationship Rules

- Use single-direction filters from dimensions to facts.
- Keep `mart_*` tables at their declared grain and avoid many-to-many relationships unless using bridge tables.
- Hide raw technical columns from report view.
- Use the DAX catalog for KPI cards instead of visual-level calculations.

