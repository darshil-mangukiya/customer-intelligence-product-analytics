# Architecture Overview

The platform moves generated source records through governed transformations, models, analytical marts, and review interfaces.

## Layered Flow

- raw data -> cleaned/staged data -> intermediate models -> feature tables -> reporting marts -> semantic KPI layer -> dashboard exports -> activation exports

## Raw Layer

- Stores generated source-like customer, product, transaction, web, engagement, support, review, loyalty, and refund data.
- Includes intentionally dirty conditions for realistic validation and observability.

## Cleaned and Staged Layer

- Standardizes channels, categories, dates, labels, statuses, returns, discounts, and invalid values.
- Creates rejected-row and audit outputs for analyst review.

## Intermediate and Feature Layer

- Creates customer, product, cohort, churn, segmentation, CLV, RFM, discount, return, engagement, and affinity features.
- Feature definitions are cataloged with grain, source, formula, and consuming dashboard/model.

## Reporting and Semantic Layer

- Publishes dimensions, facts, marts, KPI definitions, SQL logic, and DAX notes for BI consumption.
- Supports Power BI, Tableau, Streamlit, FastAPI, and activation exports.

## Activation Layer

- Creates customer lists for churn saves, win-back, high-CLV retention, cross-sell, loyalty upgrades, and discount-sensitive campaigns.
- Produces reverse-ETL-ready customer lists that mirror CRM and lifecycle marketing audience workflows.
