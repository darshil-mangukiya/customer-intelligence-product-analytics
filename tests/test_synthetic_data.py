from __future__ import annotations

import numpy as np

from etl.synthetic_data import GenerationConfig, generate_customers, generate_products, generate_transactions, generate_web_behavior


def test_synthetic_transactions_include_required_fields_and_dirty_duplicates():
    rng = np.random.default_rng(7)
    config = GenerationConfig(customers=250, products=40, orders=900, sessions=600, seed=7)
    customers = generate_customers(config.customers, rng, config)
    products = generate_products(config.products, rng, config)
    transactions = generate_transactions(customers, products, config.orders, rng, config)

    required = {
        "order_id",
        "customer_id",
        "product_id",
        "order_date",
        "quantity",
        "revenue",
        "discount",
        "return_flag",
        "cost",
        "profit",
        "region_id",
        "sales_channel",
        "order_status",
    }
    assert required.issubset(transactions.columns)
    assert len(transactions) > config.orders
    assert transactions["order_id"].duplicated().any()
    assert transactions["return_flag"].mean() > 0


def test_web_behavior_contains_sessions_and_anomaly_conditions():
    rng = np.random.default_rng(11)
    config = GenerationConfig(customers=200, products=30, orders=500, sessions=500, seed=11)
    customers = generate_customers(config.customers, rng, config)
    sessions = generate_web_behavior(customers, config.sessions, rng, config)

    assert {"session_id", "customer_id", "page_views", "traffic_source"}.issubset(sessions.columns)
    assert len(sessions) > config.sessions
    assert sessions["session_id"].duplicated().any()
    assert sessions["page_views"].max() >= 120

