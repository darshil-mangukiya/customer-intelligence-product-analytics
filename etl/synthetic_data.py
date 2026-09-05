from __future__ import annotations

import argparse
from dataclasses import dataclass

import numpy as np
import pandas as pd

from config.settings import CONFIG, ProjectConfig
from etl.io_utils import write_csv


REGIONS = pd.DataFrame(
    [
        ("R01", "West", "CA", "Los Angeles", 1.12),
        ("R02", "West", "WA", "Seattle", 1.08),
        ("R03", "West", "CO", "Denver", 0.98),
        ("R04", "South", "TX", "Austin", 1.05),
        ("R05", "South", "GA", "Atlanta", 0.96),
        ("R06", "Midwest", "IL", "Chicago", 1.00),
        ("R07", "Midwest", "OH", "Columbus", 0.91),
        ("R08", "Northeast", "NY", "New York", 1.18),
        ("R09", "Northeast", "MA", "Boston", 1.13),
        ("R10", "Southeast", "FL", "Miami", 0.94),
    ],
    columns=["region_id", "region", "state", "city", "spend_index"],
)

CATEGORIES = {
    "Apparel": ["Activewear", "Denim", "Outerwear", "Basics"],
    "Beauty": ["Skin Care", "Hair Care", "Fragrance", "Makeup"],
    "Electronics": ["Audio", "Smart Home", "Accessories", "Wearables"],
    "Home": ["Kitchen", "Bedding", "Decor", "Storage"],
    "Grocery": ["Pantry", "Coffee", "Snacks", "Beverage"],
    "Pet": ["Food", "Toys", "Wellness", "Accessories"],
    "Baby": ["Diapers", "Feeding", "Travel", "Toys"],
    "Outdoor": ["Camping", "Fitness", "Garden", "Travel"],
}

ACQUISITION_CHANNELS = {
    "Paid Search": 0.23,
    "Organic Search": 0.19,
    "Paid Social": 0.15,
    "Email": 0.10,
    "Referral": 0.11,
    "Affiliate": 0.08,
    "Marketplace": 0.09,
    "Direct": 0.05,
}

SEGMENT_SEEDS = {
    "High Value Loyal": 0.12,
    "Premium Explorers": 0.10,
    "Discount Driven": 0.20,
    "New High Intent": 0.18,
    "One Time Buyer": 0.24,
    "At Risk": 0.16,
}


@dataclass(frozen=True)
class GenerationConfig:
    customers: int = 250_000
    products: int = 1_500
    orders: int = 1_050_000
    sessions: int = 850_000
    seed: int = 42
    start_date: str = "2023-01-01"
    end_date: str = "2025-12-31"


def _choice(rng: np.random.Generator, values: list[str], size: int, p: list[float] | None = None) -> np.ndarray:
    return rng.choice(np.array(values, dtype=object), size=size, p=p)


def _weighted_dates(
    rng: np.random.Generator,
    n: int,
    start_date: str,
    end_date: str,
    holiday_lift: bool = True,
) -> pd.DatetimeIndex:
    if n == 0:
        return pd.DatetimeIndex([])

    days = pd.date_range(start_date, end_date, freq="D")
    month = days.month.to_numpy()
    dow = days.dayofweek.to_numpy()
    weights = np.ones(len(days), dtype=float)

    if holiday_lift:
        weights *= np.where(np.isin(month, [11, 12]), 1.8, 1.0)
        weights *= np.where(np.isin(month, [5, 6, 7]), 1.18, 1.0)
        weights *= np.where(np.isin(dow, [5, 6]), 1.12, 1.0)
    weights *= np.linspace(0.75, 1.25, len(days))
    weights = weights / weights.sum()
    return pd.to_datetime(rng.choice(days.to_numpy(), size=n, p=weights))


def generate_customers(n_customers: int, rng: np.random.Generator, config: GenerationConfig) -> pd.DataFrame:
    channel_values = list(ACQUISITION_CHANNELS)
    channel_probs = list(ACQUISITION_CHANNELS.values())
    segment_values = list(SEGMENT_SEEDS)
    segment_probs = list(SEGMENT_SEEDS.values())
    category_values = list(CATEGORIES)

    region_idx = rng.choice(REGIONS.index.to_numpy(), size=n_customers, p=np.array([0.16, 0.08, 0.06, 0.16, 0.08, 0.10, 0.06, 0.15, 0.06, 0.09]))
    region = REGIONS.loc[region_idx].reset_index(drop=True)
    segment_seed = _choice(rng, segment_values, n_customers, segment_probs)

    signup_dates = _weighted_dates(rng, n_customers, config.start_date, "2025-10-31")
    acquisition = _choice(rng, channel_values, n_customers, channel_probs)
    preferred_category = _choice(
        rng,
        category_values,
        n_customers,
        [0.18, 0.16, 0.12, 0.16, 0.12, 0.08, 0.06, 0.12],
    )

    loyalty_tier = np.select(
        [
            np.isin(segment_seed, ["High Value Loyal", "Premium Explorers"]),
            segment_seed == "Discount Driven",
            segment_seed == "New High Intent",
        ],
        ["Gold", "Silver", "Bronze"],
        default="Base",
    )
    loyalty_tier = np.where((segment_seed == "High Value Loyal") & (rng.random(n_customers) < 0.35), "Platinum", loyalty_tier)

    churn_status = np.select(
        [
            (segment_seed == "High Value Loyal") & (rng.random(n_customers) < 0.08),
            (segment_seed == "Premium Explorers") & (rng.random(n_customers) < 0.14),
            (segment_seed == "Discount Driven") & (rng.random(n_customers) < 0.28),
            (segment_seed == "One Time Buyer") & (rng.random(n_customers) < 0.58),
            (segment_seed == "At Risk") & (rng.random(n_customers) < 0.48),
        ],
        ["At Risk", "At Risk", "Dormant", "Churned", "At Risk"],
        default="Active",
    )

    customers = pd.DataFrame(
        {
            "customer_id": [f"C{i:08d}" for i in range(1, n_customers + 1)],
            "signup_date": signup_dates,
            "age": np.clip(rng.normal(39, 12, n_customers).round(), 18, 78).astype(int),
            "gender": _choice(rng, ["Female", "Male", "Non-Binary", "Unspecified"], n_customers, [0.48, 0.44, 0.03, 0.05]),
            "income_band": _choice(rng, ["Under 40K", "40K-75K", "75K-125K", "125K+"], n_customers, [0.18, 0.38, 0.31, 0.13]),
            "acquisition_channel": acquisition,
            "region_id": region["region_id"].to_numpy(),
            "state": region["state"].to_numpy(),
            "city": region["city"].to_numpy(),
            "loyalty_tier": loyalty_tier,
            "segment_seed": segment_seed,
            "preferred_category": preferred_category,
            "discount_sensitivity": np.clip(rng.beta(2.2, 4.8, n_customers) + (segment_seed == "Discount Driven") * 0.28, 0, 1),
            "return_propensity": np.clip(rng.beta(1.4, 16, n_customers) + (segment_seed == "Premium Explorers") * 0.04, 0, 0.55),
            "churn_status": churn_status,
        }
    )

    customers["tenure_days"] = (pd.Timestamp(config.end_date) - customers["signup_date"]).dt.days.clip(lower=0)
    customers["repeat_purchase_behavior"] = np.select(
        [
            customers["segment_seed"].eq("High Value Loyal"),
            customers["segment_seed"].eq("Premium Explorers"),
            customers["segment_seed"].eq("Discount Driven"),
            customers["segment_seed"].eq("One Time Buyer"),
        ],
        ["Frequent", "Category Explorer", "Promotion Triggered", "Low Repeat"],
        default="Developing",
    )

    dirty_idx = rng.choice(customers.index.to_numpy(), size=max(1, int(n_customers * 0.006)), replace=False)
    customers.loc[dirty_idx[: len(dirty_idx) // 2], "acquisition_channel"] = rng.choice(["paid search", "PAID_SOCIAL", "Email ", ""], size=len(dirty_idx) // 2)
    customers.loc[dirty_idx[len(dirty_idx) // 2 :], "preferred_category"] = np.nan
    return customers


def generate_products(n_products: int, rng: np.random.Generator, config: GenerationConfig) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    categories = list(CATEGORIES)
    category_probs = np.array([0.18, 0.16, 0.12, 0.15, 0.12, 0.08, 0.07, 0.12])

    for i in range(1, n_products + 1):
        category = rng.choice(categories, p=category_probs)
        sub_category = rng.choice(CATEGORIES[category])
        price_anchor = {
            "Apparel": 52,
            "Beauty": 34,
            "Electronics": 118,
            "Home": 68,
            "Grocery": 18,
            "Pet": 28,
            "Baby": 32,
            "Outdoor": 86,
        }[category]
        base_price = float(np.clip(rng.lognormal(np.log(price_anchor), 0.42), 6, 550))
        margin_rate = float(np.clip(rng.normal(0.42, 0.12), 0.08, 0.78))
        return_profile = rng.choice(["Low", "Medium", "High"], p=[0.62, 0.28, 0.10])
        if category in ["Apparel", "Electronics"]:
            return_profile = rng.choice(["Low", "Medium", "High"], p=[0.35, 0.42, 0.23])
        profitability_profile = "Premium Margin" if margin_rate > 0.52 else "Thin Margin" if margin_rate < 0.25 else "Core Margin"

        rows.append(
            {
                "product_id": f"P{i:06d}",
                "sku": f"{category[:3].upper()}-{sub_category[:3].upper()}-{i:06d}",
                "product_name": f"{sub_category} {category} Item {i:04d}",
                "category": category,
                "sub_category": sub_category,
                "base_price": round(base_price, 2),
                "unit_cost": round(base_price * (1 - margin_rate), 2),
                "margin_rate": round(margin_rate, 4),
                "lifecycle_stage": rng.choice(["Launch", "Growth", "Mature", "Decline"], p=[0.10, 0.26, 0.50, 0.14]),
                "profitability_profile": profitability_profile,
                "return_profile": return_profile,
                "retention_profile": rng.choice(["Retention Driver", "Neutral", "Churn Correlated"], p=[0.22, 0.63, 0.15]),
                "launch_date": _weighted_dates(rng, 1, "2021-01-01", config.end_date, holiday_lift=False)[0],
            }
        )
    return pd.DataFrame(rows)


def generate_transactions(
    customers: pd.DataFrame,
    products: pd.DataFrame,
    n_orders: int,
    rng: np.random.Generator,
    config: GenerationConfig,
) -> pd.DataFrame:
    segment_weight = customers["segment_seed"].map(
        {
            "High Value Loyal": 6.5,
            "Premium Explorers": 3.2,
            "Discount Driven": 2.0,
            "New High Intent": 1.5,
            "One Time Buyer": 0.45,
            "At Risk": 0.85,
        }
    ).to_numpy()
    loyalty_weight = customers["loyalty_tier"].map({"Base": 0.7, "Bronze": 1.0, "Silver": 1.3, "Gold": 2.0, "Platinum": 3.1}).to_numpy()
    active_weight = customers["churn_status"].map({"Active": 1.3, "At Risk": 0.75, "Dormant": 0.45, "Churned": 0.22}).to_numpy()
    propensity = rng.lognormal(0, 0.75, len(customers)) * segment_weight * loyalty_weight * active_weight
    propensity = propensity / propensity.sum()
    customer_idx = rng.choice(customers.index.to_numpy(), size=n_orders, p=propensity)

    product_weights = np.exp(products["margin_rate"].to_numpy()) * rng.lognormal(0, 0.45, len(products))
    product_weights *= products["lifecycle_stage"].map({"Launch": 1.1, "Growth": 1.45, "Mature": 1.0, "Decline": 0.62}).to_numpy()
    product_weights = product_weights / product_weights.sum()
    product_idx = rng.choice(products.index.to_numpy(), size=n_orders, p=product_weights)

    preferred = customers.loc[customer_idx, "preferred_category"].fillna("Unknown").to_numpy()
    for category, _subcats in CATEGORIES.items():
        mask = (preferred == category) & (rng.random(n_orders) < 0.62)
        if not mask.any():
            continue
        category_products = products.index[products["category"].eq(category)].to_numpy()
        category_weights = product_weights[category_products]
        category_weights = category_weights / category_weights.sum()
        product_idx[mask] = rng.choice(category_products, size=int(mask.sum()), p=category_weights)

    order_dates = _weighted_dates(rng, n_orders, config.start_date, config.end_date)
    churn_status = customers.loc[customer_idx, "churn_status"].to_numpy()
    churned_mask = (churn_status == "Churned") & (rng.random(n_orders) < 0.82)
    risk_mask = (churn_status == "At Risk") & (rng.random(n_orders) < 0.55)
    order_dates = pd.Series(order_dates)
    order_dates.loc[churned_mask] = _weighted_dates(rng, int(churned_mask.sum()), config.start_date, "2025-04-30")
    order_dates.loc[risk_mask] = _weighted_dates(rng, int(risk_mask.sum()), config.start_date, "2025-09-30")

    product_price = products.loc[product_idx, "base_price"].to_numpy()
    product_cost = products.loc[product_idx, "unit_cost"].to_numpy()
    region_spend = REGIONS.set_index("region_id").loc[customers.loc[customer_idx, "region_id"], "spend_index"].to_numpy()
    quantity = rng.choice([1, 2, 3, 4, 5, 6], size=n_orders, p=[0.67, 0.19, 0.07, 0.04, 0.02, 0.01])
    channel = _choice(
        rng,
        ["Web", "Mobile App", "Marketplace", "Retail Partner", "Email", "Social Shop"],
        n_orders,
        [0.38, 0.27, 0.16, 0.07, 0.07, 0.05],
    )
    discount_base = customers.loc[customer_idx, "discount_sensitivity"].to_numpy() * rng.beta(1.4, 8.5, n_orders)
    promo_lift = np.where(pd.Series(order_dates).dt.month.isin([11, 12]).to_numpy(), rng.uniform(0.03, 0.22, n_orders), 0)
    discount = np.clip(discount_base + promo_lift, 0, 0.65)

    gross_revenue = product_price * quantity * region_spend
    revenue = gross_revenue * (1 - discount)
    cost = product_cost * quantity
    return_profile_rate = products.loc[product_idx, "return_profile"].map({"Low": 0.035, "Medium": 0.085, "High": 0.18}).to_numpy()
    return_rate = np.clip(return_profile_rate + customers.loc[customer_idx, "return_propensity"].to_numpy(), 0.01, 0.55)
    return_flag = rng.random(n_orders) < return_rate
    cancelled = rng.random(n_orders) < 0.018
    order_status = np.select([cancelled, return_flag], ["Cancelled", "Returned"], default="Completed")
    profit = revenue - cost

    transactions = pd.DataFrame(
        {
            "order_id": [f"O{i:010d}" for i in range(1, n_orders + 1)],
            "customer_id": customers.loc[customer_idx, "customer_id"].to_numpy(),
            "product_id": products.loc[product_idx, "product_id"].to_numpy(),
            "order_date": pd.to_datetime(order_dates).dt.date.astype(str),
            "quantity": quantity,
            "revenue": np.round(revenue, 2),
            "discount": np.round(discount, 4),
            "return_flag": return_flag,
            "cost": np.round(cost, 2),
            "profit": np.round(profit, 2),
            "region_id": customers.loc[customer_idx, "region_id"].to_numpy(),
            "sales_channel": channel,
            "order_status": order_status,
        }
    )

    dirty_count = max(20, int(n_orders * 0.004))
    dirty_idx = rng.choice(transactions.index.to_numpy(), size=dirty_count, replace=False)
    channel_dirty = dirty_idx[: dirty_count // 3]
    transactions.loc[channel_dirty, "sales_channel"] = rng.choice(["web", "MOBILE_APP", "market place", "", None], size=len(channel_dirty))
    transactions.loc[dirty_idx[dirty_count // 3 : 2 * dirty_count // 3], "discount"] = np.nan
    outlier_idx = dirty_idx[2 * dirty_count // 3 :]
    transactions.loc[outlier_idx, "revenue"] = transactions.loc[outlier_idx, "revenue"] * rng.uniform(4, 14, len(outlier_idx))
    transactions.loc[outlier_idx, "profit"] = transactions.loc[outlier_idx, "revenue"] - transactions.loc[outlier_idx, "cost"]

    duplicate_n = max(10, int(n_orders * 0.0015))
    duplicate_rows = transactions.sample(duplicate_n, random_state=int(rng.integers(0, 1_000_000)))
    return pd.concat([transactions, duplicate_rows], ignore_index=True)


def generate_web_behavior(
    customers: pd.DataFrame,
    n_sessions: int,
    rng: np.random.Generator,
    config: GenerationConfig,
) -> pd.DataFrame:
    segment_weight = customers["segment_seed"].map(
        {
            "High Value Loyal": 3.2,
            "Premium Explorers": 2.6,
            "Discount Driven": 1.9,
            "New High Intent": 1.6,
            "One Time Buyer": 0.75,
            "At Risk": 0.9,
        }
    ).to_numpy()
    probabilities = segment_weight / segment_weight.sum()
    customer_idx = rng.choice(customers.index.to_numpy(), size=n_sessions, p=probabilities)
    segment = customers.loc[customer_idx, "segment_seed"].to_numpy()
    page_views = np.clip(rng.negative_binomial(4, 0.45, n_sessions) + 1, 1, 80)
    page_views += np.where(np.isin(segment, ["Premium Explorers", "New High Intent"]), rng.integers(0, 5, n_sessions), 0)
    bounce_prob = np.clip(0.42 - (page_views * 0.018) + (segment == "One Time Buyer") * 0.12, 0.04, 0.78)
    bounce_flag = rng.random(n_sessions) < bounce_prob
    time_spent = np.where(bounce_flag, rng.normal(31, 18, n_sessions), page_views * rng.normal(42, 14, n_sessions))
    time_spent = np.clip(time_spent, 3, 7200)

    sessions = pd.DataFrame(
        {
            "session_id": [f"S{i:011d}" for i in range(1, n_sessions + 1)],
            "customer_id": customers.loc[customer_idx, "customer_id"].to_numpy(),
            "session_date": _weighted_dates(rng, n_sessions, config.start_date, config.end_date).date.astype(str),
            "page_views": page_views,
            "time_spent": np.round(time_spent, 1),
            "bounce_flag": bounce_flag,
            "device_type": _choice(rng, ["Desktop", "Mobile", "Tablet"], n_sessions, [0.39, 0.52, 0.09]),
            "traffic_source": _choice(rng, ["Organic", "Paid Search", "Paid Social", "Email", "Referral", "Direct", "Affiliate"], n_sessions, [0.26, 0.22, 0.15, 0.12, 0.09, 0.11, 0.05]),
        }
    )

    dirty_count = max(10, int(n_sessions * 0.004))
    dirty_idx = rng.choice(sessions.index.to_numpy(), size=dirty_count, replace=False)
    sessions.loc[dirty_idx[: dirty_count // 2], "traffic_source"] = rng.choice(["organic", "paid_social", "", None], dirty_count // 2)
    sessions.loc[dirty_idx[dirty_count // 2 :], "page_views"] = rng.choice([0, 150, 250, 400], dirty_count - dirty_count // 2)
    duplicate_n = max(5, int(n_sessions * 0.001))
    sessions = pd.concat([sessions, sessions.sample(duplicate_n, random_state=int(rng.integers(0, 1_000_000)))], ignore_index=True)
    return sessions


def generate_engagement(customers: pd.DataFrame, rng: np.random.Generator, config: GenerationConfig) -> pd.DataFrame:
    n = len(customers)
    segment = customers["segment_seed"].to_numpy()
    base = np.select(
        [
            segment == "High Value Loyal",
            segment == "Premium Explorers",
            segment == "Discount Driven",
            segment == "One Time Buyer",
            segment == "At Risk",
        ],
        [68, 58, 44, 22, 26],
        default=39,
    )
    email_opens = rng.poisson(base / 4)
    clicks = rng.poisson(np.maximum(email_opens * rng.uniform(0.08, 0.38, n), 0.2))
    interactions = clicks + rng.poisson(base / 12)
    engagement_score = np.clip(base + email_opens * 1.5 + clicks * 4 + rng.normal(0, 8, n), 0, 100)
    recency_days = np.clip(120 - engagement_score + rng.normal(20, 35, n), 0, 420).round().astype(int)

    return pd.DataFrame(
        {
            "customer_id": customers["customer_id"].to_numpy(),
            "email_opens": email_opens,
            "clicks": clicks,
            "campaign_interactions": interactions,
            "last_engagement_date": (pd.Timestamp(config.end_date) - pd.to_timedelta(recency_days, unit="D")).date.astype(str),
            "engagement_score": np.round(engagement_score, 2),
        }
    )


def generate_optional_tables(
    customers: pd.DataFrame,
    products: pd.DataFrame,
    transactions: pd.DataFrame,
    rng: np.random.Generator,
    config: GenerationConfig,
) -> dict[str, pd.DataFrame]:
    support_n = max(100, int(len(customers) * 0.14))
    support_customers = rng.choice(customers["customer_id"].to_numpy(), support_n)
    support = pd.DataFrame(
        {
            "case_id": [f"CS{i:09d}" for i in range(1, support_n + 1)],
            "customer_id": support_customers,
            "case_date": _weighted_dates(rng, support_n, config.start_date, config.end_date).date.astype(str),
            "case_type": _choice(rng, ["Delivery", "Return", "Billing", "Product Question", "Complaint"], support_n, [0.28, 0.24, 0.14, 0.22, 0.12]),
            "resolution_hours": np.round(np.clip(rng.lognormal(2.1, 0.9, support_n), 0.2, 240), 2),
            "satisfaction_score": np.clip(rng.normal(4.1, 0.9, support_n), 1, 5).round(1),
        }
    )

    review_source = transactions.sample(min(len(transactions), max(100, int(len(transactions) * 0.12))), random_state=int(rng.integers(0, 1_000_000)))
    reviews = pd.DataFrame(
        {
            "review_id": [f"RV{i:09d}" for i in range(1, len(review_source) + 1)],
            "customer_id": review_source["customer_id"].to_numpy(),
            "product_id": review_source["product_id"].to_numpy(),
            "review_date": pd.to_datetime(review_source["order_date"]) + pd.to_timedelta(rng.integers(2, 45, len(review_source)), unit="D"),
            "rating": np.clip(rng.normal(4.05, 0.9, len(review_source)), 1, 5).round(0).astype(int),
            "review_sentiment": _choice(rng, ["Positive", "Neutral", "Negative"], len(review_source), [0.71, 0.18, 0.11]),
        }
    )
    reviews["review_date"] = reviews["review_date"].dt.date.astype(str)

    loyalty_n = max(100, int(len(customers) * 0.20))
    loyalty = pd.DataFrame(
        {
            "loyalty_event_id": [f"LE{i:09d}" for i in range(1, loyalty_n + 1)],
            "customer_id": rng.choice(customers["customer_id"].to_numpy(), loyalty_n),
            "event_date": _weighted_dates(rng, loyalty_n, config.start_date, config.end_date).date.astype(str),
            "event_type": _choice(rng, ["Points Earned", "Points Redeemed", "Tier Upgrade", "Tier Downgrade"], loyalty_n, [0.58, 0.29, 0.10, 0.03]),
            "points_delta": rng.integers(25, 1800, loyalty_n),
        }
    )

    categories = list(CATEGORIES)
    affinity_rows: list[dict[str, object]] = []
    for source in categories:
        for target in categories:
            if source == target:
                continue
            affinity_rows.append(
                {
                    "source_category": source,
                    "target_category": target,
                    "affinity_score_seed": round(float(rng.uniform(0.05, 0.55)), 4),
                }
            )
    affinity = pd.DataFrame(affinity_rows)

    return {
        "customer_support_interactions": support,
        "product_reviews": reviews,
        "loyalty_events": loyalty,
        "product_affinity_seed": affinity,
    }


def generate_all(config: GenerationConfig, project_config: ProjectConfig = CONFIG) -> dict[str, pd.DataFrame]:
    project_config.ensure_directories()
    rng = np.random.default_rng(config.seed)

    customers = generate_customers(config.customers, rng, config)
    products = generate_products(config.products, rng, config)
    transactions = generate_transactions(customers, products, config.orders, rng, config)
    sessions = generate_web_behavior(customers, config.sessions, rng, config)
    engagement = generate_engagement(customers, rng, config)
    optional = generate_optional_tables(customers, products, transactions, rng, config)

    tables = {
        "customers": customers,
        "products": products,
        "transactions": transactions,
        "web_behavior": sessions,
        "engagement": engagement,
        **optional,
    }
    for name, df in tables.items():
        write_csv(df, project_config.raw_dir / f"{name}.csv")

    generation_manifest = pd.DataFrame(
        [
            {"table_name": name, "rows": len(df), "columns": len(df.columns), "output_path": str(project_config.raw_dir / f"{name}.csv")}
            for name, df in tables.items()
        ]
    )
    write_csv(generation_manifest, project_config.audit_dir / "raw_generation_manifest.csv")
    return tables


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate synthetic ecommerce customer intelligence data.")
    parser.add_argument("--customers", type=int, default=GenerationConfig.customers)
    parser.add_argument("--products", type=int, default=GenerationConfig.products)
    parser.add_argument("--orders", type=int, default=GenerationConfig.orders)
    parser.add_argument("--sessions", type=int, default=GenerationConfig.sessions)
    parser.add_argument("--seed", type=int, default=GenerationConfig.seed)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    generate_all(
        GenerationConfig(
            customers=args.customers,
            products=args.products,
            orders=args.orders,
            sessions=args.sessions,
            seed=args.seed,
        )
    )


if __name__ == "__main__":
    main()
