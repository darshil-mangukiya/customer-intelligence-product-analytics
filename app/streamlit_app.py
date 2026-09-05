from __future__ import annotations

from io import StringIO

import pandas as pd
import streamlit as st

from app.data_loader import (
    LoadedDataset,
    fallback_dataset_names,
    load_dashboard_data,
    missing_dataset_names,
)


st.set_page_config(
    page_title="Customer Intelligence Platform",
    page_icon="CI",
    layout="wide",
    initial_sidebar_state="expanded",
)


PAGE_NAMES = [
    "Executive Overview",
    "Customer Segments",
    "Churn Risk",
    "CLV Analysis",
    "Cohort Retention",
    "Product Profitability",
    "Revenue Leakage",
    "Customer Drivers & Experiments",
    "Activation Lists",
    "Data Quality & Pipeline Health",
]


KPI_ALIASES = {
    "revenue": ["Total Net Revenue", "Revenue"],
    "gross_profit": ["Gross Profit"],
    "net_profit": ["Net Profit", "Total Return-adjusted Profit", "Return-adjusted Profit"],
    "margin": ["Return-adjusted Margin", "Margin %"],
    "churn": ["Churn Rate"],
    "retention": ["Retention Rate"],
    "repeat_purchase": ["Repeat Purchase Rate"],
    "aov": ["Average Order Value"],
    "clv": ["Average Historical CLV", "Predicted CLV", "Customer Lifetime Value"],
    "leakage": ["Revenue Leakage from Returns and Discounts", "Revenue Leakage from Discounts", "Revenue Leakage from Returns"],
}


def inject_css() -> None:
    st.markdown(
        """
        <style>
        .block-container {padding-top: 1.25rem; padding-bottom: 3rem;}
        div[data-testid="stMetric"] {
            background: #182235;
            border: 1px solid #334155;
            border-radius: 8px;
            padding: 14px 16px;
            box-shadow: 0 1px 2px rgba(0, 0, 0, 0.16);
        }
        div[data-testid="stMetricLabel"] {
            color: #cbd5e1;
            font-size: 0.78rem;
        }
        div[data-testid="stMetricValue"] {color: #f8fafc;}
        .section-note {
            border-left: 4px solid #2563eb;
            background: #13233a;
            color: #e2e8f0;
            padding: 0.75rem 0.9rem;
            border-radius: 6px;
            margin: 0.6rem 0 1rem 0;
        }
        .source-note {
            color: #64748b;
            font-size: 0.82rem;
            margin-top: -0.25rem;
            margin-bottom: 0.6rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def page_header(title: str, question: str, source: LoadedDataset | None = None) -> None:
    st.title(title)
    st.markdown(f"<div class='section-note'><b>Business question:</b> {question}</div>", unsafe_allow_html=True)
    if source is not None:
        st.markdown(f"<div class='source-note'>Source: {source.source_label}</div>", unsafe_allow_html=True)


def show_source(label: str, dataset: LoadedDataset) -> None:
    st.caption(f"{label} source: {dataset.source_label}")
    if dataset.note:
        st.caption(dataset.note)


def friendly_warning(dataset: LoadedDataset, action: str = "Run `make sample` or `make enterprise-upgrade` to regenerate local outputs.") -> bool:
    if not dataset.frame.empty:
        return False
    st.warning(f"{dataset.name} is unavailable. {dataset.note or action}")
    return True


def number_value(value: object, default: float = 0.0) -> float:
    try:
        if pd.isna(value):
            return default
        return float(value)
    except Exception:
        return default


def format_compact(value: float, kind: str = "number") -> str:
    if kind == "currency":
        abs_value = abs(value)
        if abs_value >= 1_000_000_000:
            return f"${value / 1_000_000_000:.1f}B"
        if abs_value >= 1_000_000:
            return f"${value / 1_000_000:.1f}M"
        if abs_value >= 1_000:
            return f"${value / 1_000:.1f}K"
        return f"${value:,.0f}"
    if kind == "percent":
        return f"{value:.1%}"
    if abs(value) >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    if abs(value) >= 1_000:
        return f"{value / 1_000:.1f}K"
    return f"{value:,.0f}"


def churn_probability_distribution(values: pd.Series) -> pd.DataFrame:
    probabilities = pd.to_numeric(values, errors="coerce").dropna().clip(0, 1)
    bands = pd.cut(
        probabilities,
        bins=[0, 0.25, 0.5, 0.75, 1.0],
        labels=["0-25%", "25-50%", "50-75%", "75-100%"],
        include_lowest=True,
    )
    counts = bands.value_counts(sort=False)
    counts.index = counts.index.astype(str)
    return counts.rename("customers").rename_axis("churn_probability_band").to_frame()


def kpi_lookup(kpis: pd.DataFrame, aliases: list[str], fallback: float | None = None) -> tuple[float | None, str]:
    if not kpis.empty and {"kpi_name", "value"}.issubset(kpis.columns):
        for alias in aliases:
            match = kpis.loc[kpis["kpi_name"].astype(str).str.lower().eq(alias.lower())]
            if not match.empty:
                return number_value(match.iloc[0]["value"]), str(match.iloc[0].get("display_format", ""))
    return fallback, ""


def metric_card(label: str, value: float | None, *, kind: str = "number", help_text: str | None = None) -> None:
    st.metric(label, "NA" if value is None else format_compact(value, kind), help=help_text)


def dataframe_preview(frame: pd.DataFrame, columns: list[str] | None = None, rows: int = 250) -> None:
    if frame.empty:
        st.info("No rows available for this preview.")
        return
    view = frame.copy()
    if columns is not None:
        selected = [col for col in columns if col in view.columns]
        if selected:
            view = view[selected]
    st.dataframe(view.head(rows), hide_index=True, use_container_width=True)


def to_csv_bytes(frame: pd.DataFrame) -> bytes:
    buffer = StringIO()
    frame.to_csv(buffer, index=False)
    return buffer.getvalue().encode("utf-8")


def group_sum(frame: pd.DataFrame, group_col: str, value_cols: list[str]) -> pd.DataFrame:
    if frame.empty or group_col not in frame.columns:
        return pd.DataFrame()
    valid = [col for col in value_cols if col in frame.columns]
    if not valid:
        return pd.DataFrame()
    grouped = frame.groupby(group_col, dropna=False)[valid].sum(numeric_only=True).sort_values(valid[0], ascending=False)
    return grouped


def group_mean(frame: pd.DataFrame, group_col: str, value_cols: list[str]) -> pd.DataFrame:
    if frame.empty or group_col not in frame.columns:
        return pd.DataFrame()
    valid = [col for col in value_cols if col in frame.columns]
    if not valid:
        return pd.DataFrame()
    return frame.groupby(group_col, dropna=False)[valid].mean(numeric_only=True).sort_values(valid[0], ascending=False)


def return_leakage_value(frame: pd.DataFrame) -> float | None:
    if frame.empty:
        return None
    if "return_loss" in frame.columns:
        return number_value(pd.to_numeric(frame["return_loss"], errors="coerce").fillna(0).sum())
    required = {"revenue", "discount", "return_flag"}
    if required.issubset(frame.columns):
        revenue = pd.to_numeric(frame["revenue"], errors="coerce").fillna(0)
        discount = pd.to_numeric(frame["discount"], errors="coerce").fillna(0).clip(lower=0, upper=1)
        returned = pd.to_numeric(frame["return_flag"], errors="coerce").fillna(0).gt(0)
        return number_value((revenue * (1 - discount) * returned).sum())
    return None


def build_sidebar(datasets: dict[str, LoadedDataset]) -> tuple[str, dict[str, list[str]]]:
    st.sidebar.title("Customer Intelligence")
    st.sidebar.caption("Synthetic ecommerce/SaaS analytics dashboard")
    st.sidebar.info("Uses synthetic/local project outputs. No real company data or production deployment is claimed.")

    page = st.sidebar.radio("Dashboard page", PAGE_NAMES)

    clv = datasets["clv"].frame
    churn = datasets["churn"].frame
    customer = datasets["customer_overview"].frame
    activation_segment_values = [
        datasets[name].frame.get("segment", pd.Series(dtype=str))
        for name in [
            "activation_churn",
            "activation_winback",
            "activation_high_clv",
            "activation_cross_sell",
            "activation_loyalty",
            "activation_discount",
        ]
    ]

    channels = sorted(
        set(
            pd.concat(
                [
                    clv.get("acquisition_channel", pd.Series(dtype=str)),
                    churn.get("acquisition_channel", pd.Series(dtype=str)),
                    customer.get("acquisition_channel", pd.Series(dtype=str)),
                ],
                ignore_index=True,
            ).dropna()
        )
    )
    segments = sorted(
        set(
            pd.concat(
                [
                    clv.get("segment_seed", pd.Series(dtype=str)),
                    churn.get("segment_name", pd.Series(dtype=str)),
                    churn.get("segment", pd.Series(dtype=str)),
                    customer.get("segment_seed", pd.Series(dtype=str)),
                    *activation_segment_values,
                ],
                ignore_index=True,
            ).dropna()
        )
    )
    risks = sorted(set(churn.get("churn_risk_tier", pd.Series(dtype=str)).dropna()))
    clv_bands = sorted(set(pd.concat([clv.get("clv_band", pd.Series(dtype=str)), churn.get("clv_band", pd.Series(dtype=str))], ignore_index=True).dropna()))

    with st.sidebar.expander("Global filters", expanded=True):
        selected_channels = st.multiselect("Acquisition channel", channels, default=channels)
        selected_segments = st.multiselect("Segment", segments, default=segments)
        selected_risks = st.multiselect("Churn risk tier", risks, default=risks)
        selected_clv_bands = st.multiselect("CLV band", clv_bands, default=clv_bands)

    fallback_names = fallback_dataset_names(datasets)
    if fallback_names:
        st.sidebar.warning("Sample fallback loaded: " + ", ".join(fallback_names[:5]) + ("..." if len(fallback_names) > 5 else ""))
    missing = missing_dataset_names(datasets)
    if missing:
        st.sidebar.caption(f"Missing optional datasets: {len(missing)}")

    return page, {
        "channels": selected_channels or channels,
        "segments": selected_segments or segments,
        "risks": selected_risks or risks,
        "clv_bands": selected_clv_bands or clv_bands,
    }


def filter_by_common_fields(frame: pd.DataFrame, filters: dict[str, list[str]]) -> pd.DataFrame:
    if frame.empty:
        return frame
    view = frame.copy()
    if filters["channels"] and "acquisition_channel" in view.columns:
        view = view.loc[view["acquisition_channel"].isin(filters["channels"])]
    if filters["risks"] and "churn_risk_tier" in view.columns:
        view = view.loc[view["churn_risk_tier"].isin(filters["risks"])]
    if filters["clv_bands"] and "clv_band" in view.columns:
        view = view.loc[view["clv_band"].isin(filters["clv_bands"])]
    if filters["segments"]:
        for segment_col in ["segment_seed", "segment_name", "segment"]:
            if segment_col in view.columns:
                view = view.loc[view[segment_col].isin(filters["segments"])]
                break
    return view


def page_executive(datasets: dict[str, LoadedDataset], filters: dict[str, list[str]]) -> None:
    page_header(
        "Executive Overview",
        "Are revenue, profit, retention, customer value, leakage, and activation priorities moving in the right direction?",
        datasets["kpis"],
    )
    kpis = datasets["kpis"].frame
    customer = filter_by_common_fields(datasets["customer_overview"].frame, filters)
    churn = filter_by_common_fields(datasets["churn"].frame, filters)
    clv = filter_by_common_fields(datasets["clv"].frame, filters)
    product = datasets["product"].frame

    revenue, revenue_fmt = kpi_lookup(kpis, KPI_ALIASES["revenue"], customer.get("net_revenue", pd.Series(dtype=float)).sum())
    profit, _ = kpi_lookup(kpis, KPI_ALIASES["net_profit"], customer.get("return_adjusted_profit", pd.Series(dtype=float)).sum())
    churn_rate, _ = kpi_lookup(kpis, KPI_ALIASES["churn"], churn.get("churn_probability", pd.Series(dtype=float)).mean())
    retention_rate, _ = kpi_lookup(kpis, KPI_ALIASES["retention"], None if churn_rate is None else 1 - churn_rate)
    repeat_rate, _ = kpi_lookup(kpis, KPI_ALIASES["repeat_purchase"], customer.get("repeat_purchase_flag", pd.Series(dtype=float)).mean())
    aov, _ = kpi_lookup(kpis, KPI_ALIASES["aov"], None)
    if aov is None and "net_revenue" in customer and "orders" in customer:
        orders = customer["orders"].sum()
        aov = customer["net_revenue"].sum() / orders if orders else None
    predicted_clv = clv.get("predicted_12m_clv", pd.Series(dtype=float)).mean() if "predicted_12m_clv" in clv else None
    leakage, _ = kpi_lookup(kpis, KPI_ALIASES["leakage"], product.get("discount_amount", pd.Series(dtype=float)).sum())

    cols = st.columns(5)
    with cols[0]:
        metric_card("Revenue", revenue, kind="currency")
    with cols[1]:
        metric_card("Return-adjusted profit", profit, kind="currency")
    with cols[2]:
        metric_card("Churn rate", churn_rate, kind="percent")
    with cols[3]:
        metric_card("Retention rate", retention_rate, kind="percent")
    with cols[4]:
        metric_card("Revenue leakage", leakage, kind="currency")

    cols = st.columns(4)
    with cols[0]:
        metric_card("Repeat purchase rate", repeat_rate, kind="percent")
    with cols[1]:
        metric_card("Average order value", aov, kind="currency")
    with cols[2]:
        metric_card("Predicted CLV", predicted_clv, kind="currency")
    with cols[3]:
        metric_card("Customers in view", float(len(customer)))

    left, right = st.columns([1.2, 1])
    with left:
        st.subheader("Revenue and profit trend")
        trend = datasets["revenue_profit_forecast"].frame
        if trend.empty:
            st.info("Revenue trend output is optional. Run `make advanced` to generate forecast trend files.")
        elif "month_start" in trend.columns:
            chart = trend.set_index("month_start")[[col for col in ["revenue_forecast", "profit_forecast"] if col in trend.columns]]
            st.line_chart(chart)
        else:
            dataframe_preview(trend)

    with right:
        st.subheader("Activation priority summary")
        activation = datasets["activation_manifest"].frame
        if activation.empty:
            counts = pd.DataFrame(
                [
                    {"activation_list": name, "customers": len(datasets[key].frame)}
                    for name, key in [
                        ("Churn", "activation_churn"),
                        ("Win-back", "activation_winback"),
                        ("High CLV", "activation_high_clv"),
                        ("Cross-sell", "activation_cross_sell"),
                        ("Loyalty", "activation_loyalty"),
                        ("Discount-sensitive", "activation_discount"),
                    ]
                ]
            )
            st.bar_chart(counts.set_index("activation_list"))
        else:
            st.bar_chart(activation.set_index("export_name")["sample_rows" if "sample_rows" in activation.columns else "rows"])
        show_source("Activation", datasets["activation_manifest"])

    left, right = st.columns([1, 1])
    with left:
        st.subheader("Customer segment contribution")
        segments = datasets["segments"].frame
        if segments.empty:
            st.info("Segment summary is optional. Run segmentation assets to populate this view.")
        else:
            idx_col = "segment_name" if "segment_name" in segments.columns else segments.columns[0]
            value_cols = [col for col in ["revenue", "profit", "customers"] if col in segments.columns]
            if value_cols:
                st.bar_chart(segments.set_index(idx_col)[value_cols])
    with right:
        st.subheader("Top categories by profit")
        category = group_sum(product, "category", ["return_adjusted_profit", "net_revenue"])
        if category.empty:
            st.info("Category profit view is unavailable.")
        else:
            st.bar_chart(category.head(10))

    st.subheader("Executive interpretation")
    st.write(
        "Use this page to separate customer growth from customer quality. The most useful executive read is the combination of retention, CLV, return-adjusted profit, leakage, and activation queue size."
    )


def page_segments(datasets: dict[str, LoadedDataset], filters: dict[str, list[str]]) -> None:
    page_header(
        "Customer Segments",
        "Which customer groups contribute revenue/profit, retain better, and need different actions?",
        datasets["segments"],
    )
    segments = datasets["segments"].frame
    profiles = datasets["segment_profiles"].frame
    customer = filter_by_common_fields(datasets["customer_overview"].frame, filters)

    if segments.empty and customer.empty:
        friendly_warning(datasets["segments"])
        return

    if segments.empty:
        group_col = "segment_seed" if "segment_seed" in customer.columns else "loyalty_tier"
        segments = (
            customer.groupby(group_col, dropna=False)
            .agg(
                customers=("customer_id", "nunique"),
                revenue=("net_revenue", "sum"),
                profit=("return_adjusted_profit", "sum"),
                churn_rate=("churn_label", "mean"),
                repeat_purchase_rate=("repeat_purchase_flag", "mean"),
                avg_clv=("historical_clv", "mean"),
            )
            .reset_index()
            .rename(columns={group_col: "segment_name"})
        )

    cols = st.columns(4)
    cols[0].metric("Segments", f"{segments['segment_name'].nunique() if 'segment_name' in segments else len(segments):,}")
    cols[1].metric("Customers", f"{number_value(segments.get('customers', pd.Series(dtype=float)).sum()):,.0f}")
    cols[2].metric("Revenue", format_compact(number_value(segments.get("revenue", pd.Series(dtype=float)).sum()), "currency"))
    cols[3].metric("Profit", format_compact(number_value(segments.get("profit", pd.Series(dtype=float)).sum()), "currency"))

    left, right = st.columns([1, 1])
    with left:
        st.subheader("Segment revenue and profit")
        chart_cols = [col for col in ["revenue", "profit"] if col in segments.columns]
        if chart_cols and "segment_name" in segments.columns:
            st.bar_chart(segments.set_index("segment_name")[chart_cols])
    with right:
        st.subheader("Churn and CLV by segment")
        metric_cols = [col for col in ["churn_rate", "avg_historical_clv", "avg_clv", "discount_dependency", "return_rate"] if col in segments.columns]
        if metric_cols and "segment_name" in segments.columns:
            st.bar_chart(segments.set_index("segment_name")[metric_cols].head(12))

    st.subheader("Segment action table")
    if not profiles.empty:
        dataframe_preview(
            profiles,
            ["segment_name", "customers", "customer_share", "value_score", "business_recommendation"],
            rows=100,
        )
    else:
        dataframe_preview(segments, rows=100)
    st.write("Interpretation: prioritize segments by profit contribution, churn exposure, CLV, and discount dependency rather than by size alone.")


def page_churn(datasets: dict[str, LoadedDataset], filters: dict[str, list[str]]) -> None:
    page_header("Churn Risk", "Which customers and groups should be prioritized before they lapse?", datasets["churn"])
    churn = filter_by_common_fields(datasets["churn"].frame, filters)
    clv = filter_by_common_fields(datasets["clv"].frame, filters)
    if friendly_warning(datasets["churn"]):
        return
    if churn.empty:
        st.warning("No churn rows match the selected filters.")
        return

    if "churn_probability" not in churn.columns and "churn_label" in churn.columns:
        churn["churn_probability"] = churn["churn_label"]
    if "churn_risk_tier" not in churn.columns and "churn_probability" in churn.columns:
        churn["churn_risk_tier"] = pd.cut(
            churn["churn_probability"],
            bins=[-0.01, 0.25, 0.5, 0.75, 1.0],
            labels=["Low", "Medium", "High", "Critical"],
        ).astype(str)

    cols = st.columns(4)
    cols[0].metric("Customers in risk view", f"{len(churn):,}")
    cols[1].metric("Avg churn probability", format_compact(number_value(churn.get("churn_probability", pd.Series(dtype=float)).mean()), "percent"))
    cols[2].metric("Expected profit at risk", format_compact(number_value(churn.get("expected_profit_at_risk", pd.Series(dtype=float)).sum()), "currency"))
    high_share = churn.get("churn_risk_tier", pd.Series(dtype=str)).isin(["High", "Critical"]).mean()
    cols[3].metric("High/Critical share", format_compact(number_value(high_share), "percent"))

    left, right = st.columns([1, 1])
    with left:
        st.subheader("Risk tier distribution")
        tier = churn.groupby("churn_risk_tier", dropna=False).agg(customers=("customer_id", "nunique")).sort_values("customers", ascending=False)
        st.bar_chart(tier)
    with right:
        st.subheader("Churn probability distribution")
        if "churn_probability" in churn.columns:
            st.bar_chart(churn_probability_distribution(churn["churn_probability"]))

    left, right = st.columns([1.1, 1])
    with left:
        st.subheader("Top churn drivers")
        drivers = datasets["churn_drivers"].frame
        dataframe_preview(drivers, ["feature", "direction", "importance", "business_interpretation"], rows=12)
        show_source("Drivers", datasets["churn_drivers"])
    with right:
        st.subheader("Risk by channel/category")
        for group_col in ["acquisition_channel", "top_purchase_category", "segment", "segment_name"]:
            if group_col in churn.columns:
                chart = group_mean(churn, group_col, ["churn_probability", "expected_profit_at_risk"]).head(12)
                if not chart.empty:
                    st.bar_chart(chart)
                    break

    st.subheader("High-risk customer queue")
    queue = churn.copy()
    if not clv.empty and "customer_id" in queue.columns and "customer_id" in clv.columns:
        add_cols = [col for col in ["customer_id", "predicted_12m_clv", "clv_band", "expected_clv_at_risk"] if col in clv.columns]
        queue = queue.merge(clv[add_cols].drop_duplicates("customer_id"), on="customer_id", how="left", suffixes=("", "_clv"))
    dataframe_preview(
        queue.sort_values([col for col in ["expected_profit_at_risk", "churn_probability"] if col in queue.columns], ascending=False),
        ["customer_id", "segment", "segment_name", "churn_probability", "churn_risk_tier", "clv_band", "predicted_12m_clv", "expected_profit_at_risk", "recommended_action", "top_purchase_category"],
        rows=500,
    )
    st.write("Interpretation: retention priority is strongest where high churn probability overlaps with high CLV or profit exposure.")


def page_clv(datasets: dict[str, LoadedDataset], filters: dict[str, list[str]]) -> None:
    page_header("CLV Analysis", "Which customers and channels create the most future value, and where is value at risk?", datasets["clv"])
    clv = filter_by_common_fields(datasets["clv"].frame, filters)
    churn = filter_by_common_fields(datasets["churn"].frame, filters)
    if friendly_warning(datasets["clv"]):
        return
    if clv.empty:
        st.warning("No CLV rows match the selected filters.")
        return

    value_col = "predicted_12m_clv" if "predicted_12m_clv" in clv.columns else "historical_clv" if "historical_clv" in clv.columns else "priority_score"
    cols = st.columns(4)
    cols[0].metric("Customers", f"{len(clv):,}")
    cols[1].metric("Avg CLV", format_compact(number_value(clv.get(value_col, pd.Series(dtype=float)).mean()), "currency"))
    cols[2].metric("Total CLV", format_compact(number_value(clv.get(value_col, pd.Series(dtype=float)).sum()), "currency"))
    cols[3].metric("CLV at risk", format_compact(number_value(clv.get("expected_clv_at_risk", pd.Series(dtype=float)).sum()), "currency"))

    left, right = st.columns([1, 1])
    with left:
        st.subheader("CLV by segment")
        segment_view = datasets["clv_segment"].frame
        if not segment_view.empty and "segment_seed" in segment_view.columns:
            st.bar_chart(segment_view.set_index("segment_seed")[[col for col in ["avg_predicted_12m_clv", "predicted_12m_clv", "expected_clv_at_risk"] if col in segment_view.columns]])
        else:
            for group_col in ["segment_seed", "segment", "segment_name"]:
                chart = group_mean(clv, group_col, [value_col])
                if not chart.empty:
                    st.bar_chart(chart.head(12))
                    break
    with right:
        st.subheader("CLV by acquisition channel")
        channel_view = datasets["clv_channel"].frame
        if not channel_view.empty and "acquisition_channel" in channel_view.columns:
            st.bar_chart(channel_view.set_index("acquisition_channel")[[col for col in ["avg_predicted_12m_clv", "predicted_12m_clv", "expected_clv_at_risk"] if col in channel_view.columns]])
        else:
            chart = group_mean(clv, "acquisition_channel", [value_col])
            if not chart.empty:
                st.bar_chart(chart.head(12))

    st.subheader("CLV vs churn exposure")
    if not churn.empty and "customer_id" in clv.columns and "customer_id" in churn.columns:
        exposure = clv.merge(
            churn[[col for col in ["customer_id", "churn_probability", "churn_risk_tier"] if col in churn.columns]].drop_duplicates("customer_id"),
            on="customer_id",
            how="left",
        )
        if {"churn_risk_tier", value_col}.issubset(exposure.columns):
            st.bar_chart(exposure.groupby("churn_risk_tier")[value_col].mean().sort_values(ascending=False))
    else:
        st.info("Churn and CLV overlap is optional and depends on generated mart availability.")

    st.subheader("High-value customer table")
    dataframe_preview(
        clv.sort_values(value_col, ascending=False),
        ["customer_id", "segment", "segment_seed", "acquisition_channel", "orders", "historical_clv", "predicted_12m_clv", "clv_band", "expected_clv_at_risk", "churn_probability", "recommended_action"],
        rows=500,
    )
    st.write("Interpretation: retention spend should be evaluated against predicted value and churn exposure together.")


def page_cohort(datasets: dict[str, LoadedDataset], filters: dict[str, list[str]]) -> None:
    page_header("Cohort Retention", "How do acquisition cohorts retain customers and revenue from Month 1 through Month 12?", datasets["cohort"])
    cohort = datasets["cohort"].frame
    heatmap = datasets["cohort_heatmap"].frame
    if friendly_warning(datasets["cohort"]):
        return

    retention_col = "retention_rate"
    month_col = "cohort_index"
    cols = st.columns(4)
    for idx, month in enumerate([1, 3, 6, 12]):
        value = None
        if {month_col, retention_col}.issubset(cohort.columns):
            value = cohort.loc[cohort[month_col].eq(month), retention_col].mean()
        cols[idx].metric(f"Month {month} retention", "NA" if pd.isna(value) else format_compact(number_value(value), "percent"))

    st.subheader("Cohort retention matrix")
    if not heatmap.empty:
        pct_cols = [col for col in heatmap.columns if col.startswith("month_")]
        styled = heatmap.copy()
        st.dataframe(
            styled.style.format({col: "{:.1%}" for col in pct_cols}).background_gradient(cmap="Blues", subset=pct_cols),
            use_container_width=True,
        )
        show_source("Heatmap", datasets["cohort_heatmap"])
    elif {"cohort_month", "cohort_index", "retention_rate"}.issubset(cohort.columns):
        matrix = cohort.pivot_table(index="cohort_month", columns="cohort_index", values="retention_rate", aggfunc="mean")
        st.dataframe(matrix.style.format("{:.1%}").background_gradient(cmap="Blues"), use_container_width=True)

    left, right = st.columns([1, 1])
    with left:
        st.subheader("Month-index retention trend")
        if {month_col, retention_col}.issubset(cohort.columns):
            st.line_chart(cohort.groupby(month_col)[retention_col].mean())
    with right:
        st.subheader("Revenue retention trend")
        if {"cohort_index", "revenue_retention_rate"}.issubset(cohort.columns):
            st.line_chart(cohort.groupby("cohort_index")["revenue_retention_rate"].mean())
        else:
            st.info("Revenue retention is available after the cohort mart is generated.")

    col_a, col_b = st.columns([1, 1])
    with col_a:
        st.subheader("Retention by acquisition channel")
        channel = datasets["retention_channel"].frame
        if not channel.empty and {"acquisition_channel", "cohort_index", "retention_rate"}.issubset(channel.columns):
            view = channel.loc[channel["cohort_index"].isin([1, 3, 6, 12])]
            st.bar_chart(view.pivot_table(index="acquisition_channel", columns="cohort_index", values="retention_rate"))
        else:
            st.info("Channel retention output is optional.")
    with col_b:
        st.subheader("Retention by first category")
        category = datasets["retention_category"].frame
        if not category.empty and {"first_product_category", "cohort_index", "retention_rate"}.issubset(category.columns):
            view = category.loc[category["cohort_index"].isin([1, 3, 6, 12])]
            st.bar_chart(view.pivot_table(index="first_product_category", columns="cohort_index", values="retention_rate"))
        else:
            st.info("First-category retention output is optional.")
    st.write("Interpretation: cohort retention separates acquisition volume from durable customer quality.")


def page_product(datasets: dict[str, LoadedDataset], filters: dict[str, list[str]]) -> None:
    page_header("Product Profitability", "Which products and categories create profit after returns and discounts?", datasets["product"])
    product = datasets["product"].frame
    if friendly_warning(datasets["product"]):
        return

    if "net_revenue" not in product.columns and "price" in product.columns:
        product["net_revenue"] = product["price"]
    if "return_adjusted_profit" not in product.columns:
        product["return_adjusted_profit"] = product.get("profit", product.get("margin", pd.Series(dtype=float)))

    cols = st.columns(4)
    cols[0].metric("Products", f"{product.get('product_id', pd.Series(dtype=str)).nunique():,}")
    cols[1].metric("Revenue", format_compact(number_value(product.get("net_revenue", pd.Series(dtype=float)).sum()), "currency"))
    cols[2].metric("Return-adjusted profit", format_compact(number_value(product.get("return_adjusted_profit", pd.Series(dtype=float)).sum()), "currency"))
    cols[3].metric("Avg return rate", format_compact(number_value(product.get("return_rate", pd.Series(dtype=float)).mean()), "percent"))

    left, right = st.columns([1, 1])
    with left:
        st.subheader("Category profitability")
        category = group_sum(product, "category", ["net_revenue", "return_adjusted_profit"])
        if not category.empty:
            st.bar_chart(category.head(12))
    with right:
        st.subheader("Return-heavy and low-margin flags")
        flag_col = "product_performance_flag"
        if flag_col in product.columns:
            st.bar_chart(product.groupby(flag_col).size().rename("products"))
        else:
            st.info("Product flags are available after product mart generation.")

    tabs = st.tabs(["Top revenue products", "Top profit products", "Low-margin high-volume", "Return-heavy", "Affinity / cross-sell"])
    with tabs[0]:
        dataframe_preview(product.sort_values("net_revenue", ascending=False) if "net_revenue" in product else product, ["product_id", "product_name", "category", "orders", "net_revenue", "return_adjusted_profit", "return_rate", "discount_dependency"], rows=250)
    with tabs[1]:
        dataframe_preview(product.sort_values("return_adjusted_profit", ascending=False) if "return_adjusted_profit" in product else product, ["product_id", "product_name", "category", "orders", "net_revenue", "return_adjusted_profit", "return_adjusted_margin"], rows=250)
    with tabs[2]:
        low_margin = datasets["low_margin"].frame
        dataframe_preview(low_margin if not low_margin.empty else product.loc[product.get("product_performance_flag", pd.Series(dtype=str)).eq("Low Margin High Volume")], rows=250)
    with tabs[3]:
        return_heavy = datasets["return_heavy"].frame
        dataframe_preview(return_heavy if not return_heavy.empty else product.sort_values("return_rate", ascending=False) if "return_rate" in product else product, rows=250)
    with tabs[4]:
        affinity = datasets["affinity"].frame
        dataframe_preview(affinity, rows=250)
    st.write("Interpretation: product decisions should use return-adjusted profit and leakage, not revenue alone.")


def page_leakage(datasets: dict[str, LoadedDataset], filters: dict[str, list[str]]) -> None:
    page_header("Revenue Leakage", "Where are returns and discounts eroding revenue quality?", datasets["product"])
    product = datasets["product"].frame
    orders = filter_by_common_fields(datasets["orders"].frame, filters)
    churn = filter_by_common_fields(datasets["churn"].frame, filters)
    if friendly_warning(datasets["product"]):
        return

    discount = number_value(product.get("discount_amount", pd.Series(dtype=float)).sum())
    return_loss = return_leakage_value(orders)
    avg_return = number_value(product.get("return_rate", pd.Series(dtype=float)).mean())
    avg_discount = number_value(product.get("discount_dependency", pd.Series(dtype=float)).mean())
    margin = number_value(product.get("return_adjusted_margin", pd.Series(dtype=float)).mean())

    cols = st.columns(5)
    cols[0].metric("Discount leakage", format_compact(discount, "currency"))
    cols[1].metric("Return leakage", "NA" if return_loss is None else format_compact(return_loss, "currency"))
    cols[2].metric("Avg return rate", format_compact(avg_return, "percent"))
    cols[3].metric("Avg discount dependency", format_compact(avg_discount, "percent"))
    cols[4].metric("Avg margin", format_compact(margin, "percent"))

    left, right = st.columns([1, 1])
    with left:
        st.subheader("Return rate by category")
        chart = group_mean(product, "category", ["return_rate", "discount_dependency", "return_adjusted_margin"])
        if not chart.empty:
            st.bar_chart(chart.head(12))
    with right:
        st.subheader("Margin leakage ranking")
        if {"category", "discount_amount", "return_adjusted_profit"}.issubset(product.columns):
            leakage = group_sum(product, "category", ["discount_amount", "return_adjusted_profit"])
            st.bar_chart(leakage.head(12))

    st.subheader("Products to investigate")
    sorted_product = product.copy()
    sort_cols = [col for col in ["return_rate", "discount_dependency", "orders"] if col in sorted_product.columns]
    if sort_cols:
        sorted_product = sorted_product.sort_values(sort_cols, ascending=False)
    dataframe_preview(sorted_product, ["product_id", "product_name", "category", "orders", "net_revenue", "return_adjusted_profit", "return_rate", "discount_dependency", "product_performance_flag"], rows=300)

    st.subheader("Discount-sensitive churn exposure")
    if churn.empty:
        st.info("Churn output is optional for this view.")
    else:
        sort_cols = [col for col in ["discount_dependency", "expected_profit_at_risk", "churn_probability"] if col in churn.columns]
        dataframe_preview(churn.sort_values(sort_cols, ascending=False) if sort_cols else churn, ["customer_id", "churn_probability", "churn_risk_tier", "discount_dependency", "expected_profit_at_risk", "top_purchase_category"], rows=250)
    st.write("Interpretation: leakage review should separate return problems from promotion dependency before changing pricing or merchandising strategy.")


def page_activation(datasets: dict[str, LoadedDataset], filters: dict[str, list[str]]) -> None:
    page_header("Activation Lists", "Which customer audiences are ready for lifecycle, retention, loyalty, or cross-sell action?", datasets["activation_manifest"])
    exports = {
        "Churn campaign": datasets["activation_churn"],
        "Win-back campaign": datasets["activation_winback"],
        "High-CLV customers": datasets["activation_high_clv"],
        "Cross-sell targets": datasets["activation_cross_sell"],
        "Loyalty upgrade targets": datasets["activation_loyalty"],
        "Discount-sensitive customers": datasets["activation_discount"],
    }
    counts = pd.DataFrame(
        {
            "activation_list": name,
            "rows_loaded": len(dataset.frame),
            "source": dataset.source_label,
        }
        for name, dataset in exports.items()
    )
    col_a, col_b = st.columns([1, 1])
    with col_a:
        st.subheader("Export coverage")
        st.bar_chart(counts.set_index("activation_list")["rows_loaded"])
    with col_b:
        st.subheader("Export manifest")
        manifest = datasets["activation_manifest"].frame
        dataframe_preview(
            manifest if not manifest.empty else counts,
            ["export_name", "rows", "sample_rows", "grain", "activation_owner"],
            rows=20,
        )

    selected = st.selectbox("Activation list", list(exports.keys()))
    selected_dataset = exports[selected]
    selected_frame = filter_by_common_fields(selected_dataset.frame, filters)
    show_source(selected, selected_dataset)
    if selected_frame.empty:
        st.info("No activation rows are available for the selected filters.")
        return
    c1, c2, c3 = st.columns(3)
    c1.metric("Rows loaded", f"{len(selected_frame):,}")
    c2.metric("Avg priority", f"{number_value(selected_frame.get('priority_score', pd.Series(dtype=float)).mean()):.1f}")
    c3.metric("Avg churn probability", format_compact(number_value(selected_frame.get("churn_probability", pd.Series(dtype=float)).mean()), "percent"))
    st.download_button(
        label=f"Download {selected} CSV",
        data=to_csv_bytes(selected_frame),
        file_name=selected.lower().replace(" ", "_").replace("-", "_") + ".csv",
        mime="text/csv",
    )
    dataframe_preview(selected_frame.sort_values("priority_score", ascending=False) if "priority_score" in selected_frame else selected_frame, rows=500)
    st.write("Interpretation: activation exports are local reverse-ETL style files for campaign planning and are not connected to a live CRM.")


def page_quality(datasets: dict[str, LoadedDataset], filters: dict[str, list[str]]) -> None:
    page_header("Data Quality & Pipeline Health", "Are marts, validation outputs, anomalies, rejected rows, and scoring outputs healthy enough for local reporting?", datasets["quality"])
    quality = datasets["quality"].frame
    freshness = datasets["freshness"].frame
    anomalies = datasets["anomalies"].frame
    rejected = datasets["rejected"].frame
    audit = datasets["audit"].frame
    scoring = datasets["model_scoring"].frame

    cols = st.columns(5)
    failing_checks = number_value(quality.get("failing_checks", pd.Series(dtype=float)).sum()) if not quality.empty else None
    rejected_rows = number_value(rejected.get("rejected_rows", pd.Series(dtype=float)).sum()) if not rejected.empty else None
    anomaly_count = len(anomalies) if not anomalies.empty else 0
    stale_assets = number_value(freshness.get("freshness_status", pd.Series(dtype=str)).astype(str).str.upper().eq("STALE").sum()) if not freshness.empty else None
    scored_rows = number_value(scoring.get("rows_scored", pd.Series(dtype=float)).sum()) if not scoring.empty else None
    cols[0].metric("Failing checks", "NA" if failing_checks is None else f"{failing_checks:,.0f}")
    cols[1].metric("Rejected rows", "NA" if rejected_rows is None else f"{rejected_rows:,.0f}")
    cols[2].metric("Anomalies logged", f"{anomaly_count:,.0f}")
    cols[3].metric("Stale assets", "NA" if stale_assets is None else f"{stale_assets:,.0f}")
    cols[4].metric("Rows scored", "NA" if scored_rows is None else format_compact(scored_rows))

    left, right = st.columns([1, 1])
    with left:
        st.subheader("Validation status")
        if quality.empty:
            friendly_warning(datasets["quality"])
        else:
            st.bar_chart(quality.groupby("status")["checks"].sum())
            dataframe_preview(quality, rows=100)
    with right:
        st.subheader("Mart freshness")
        if freshness.empty:
            friendly_warning(datasets["freshness"])
        else:
            st.bar_chart(freshness.groupby("freshness_status")["row_count"].count())
            dataframe_preview(freshness, ["asset_name", "layer", "row_count", "age_hours", "freshness_status", "owner"], rows=100)

    tabs = st.tabs(["Anomaly log", "Rejected rows", "Pipeline audit", "Model scoring"])
    with tabs[0]:
        dataframe_preview(anomalies, rows=200)
    with tabs[1]:
        dataframe_preview(rejected, rows=200)
    with tabs[2]:
        dataframe_preview(audit, rows=200)
    with tabs[3]:
        dataframe_preview(scoring, rows=200)
    st.write("Interpretation: this page is the local publication gate before trusting dashboard marts and model-scoring outputs.")


def page_statistical_insights(datasets: dict[str, LoadedDataset], filters: dict[str, list[str]]) -> None:
    page_header(
        "Customer Drivers & Experiments",
        "Which differences are statistically detectable, practically meaningful, and useful for a next decision?",
        datasets["statistical_tests"],
    )
    tests = datasets["statistical_tests"].frame
    experiment = datasets["experiment_evaluation"].frame
    churn = datasets["statistical_churn_drivers"].frame
    clv = datasets["clv_drivers"].frame
    if tests.empty or experiment.empty:
        st.warning("Statistical outputs are unavailable. Run `make analytics` after generating project marts.")
        return
    exp = experiment.iloc[0]
    columns = st.columns(5)
    columns[0].metric("Questions evaluated", f"{len(tests):,}")
    columns[1].metric("Detectable findings", f"{tests['statistically_significant'].astype(str).str.lower().eq('true').sum():,}")
    columns[2].metric("Experiment absolute lift", format_compact(number_value(exp.get("absolute_difference")), "percent"))
    columns[3].metric("95% CI", f"{number_value(exp.get('confidence_interval_low')):.1%} to {number_value(exp.get('confidence_interval_high')):.1%}")
    columns[4].metric("Practical significance", "Yes" if str(exp.get("practically_significant")).lower() == "true" else "No")
    st.info(str(exp.get("decision", "No decision generated.")))

    left, right = st.columns(2)
    with left:
        st.subheader("Churn-associated drivers")
        if not churn.empty:
            chart = churn.head(10).set_index("metric_or_driver")[["importance_or_strength"]]
            st.bar_chart(chart)
            dataframe_preview(churn, ["metric_or_driver", "effect_direction", "effect_size", "p_value", "business_interpretation"], 10)
    with right:
        st.subheader("CLV-associated drivers")
        if not clv.empty:
            chart = clv.head(10).set_index("metric_or_driver")[["importance_or_strength"]]
            st.bar_chart(chart)
            dataframe_preview(clv, ["metric_or_driver", "effect_direction", "effect_size", "p_value", "business_interpretation"], 10)

    st.subheader("Decision-oriented statistical findings")
    dataframe_preview(tests, ["business_question", "statistical_method", "p_value", "statistically_significant", "effect_size_name", "effect_size", "effect_magnitude", "business_interpretation", "recommended_action", "kpi_to_monitor"], 20)
    with st.expander("Methodology and limitations"):
        st.write("Two-sided tests use alpha 0.05, 95% confidence intervals, and method-appropriate effect sizes. Statistical significance is shown separately from a two-percentage-point experiment practical threshold.")
        st.write("All inputs and experiment outcomes are synthetic. Driver rankings and regression results are associations, not causal effects, and require validation on real-world data.")


def main() -> None:
    inject_css()
    datasets = load_dashboard_data()
    page, filters = build_sidebar(datasets)

    if page == "Executive Overview":
        page_executive(datasets, filters)
    elif page == "Customer Segments":
        page_segments(datasets, filters)
    elif page == "Churn Risk":
        page_churn(datasets, filters)
    elif page == "CLV Analysis":
        page_clv(datasets, filters)
    elif page == "Cohort Retention":
        page_cohort(datasets, filters)
    elif page == "Product Profitability":
        page_product(datasets, filters)
    elif page == "Revenue Leakage":
        page_leakage(datasets, filters)
    elif page == "Customer Drivers & Experiments":
        page_statistical_insights(datasets, filters)
    elif page == "Activation Lists":
        page_activation(datasets, filters)
    elif page == "Data Quality & Pipeline Health":
        page_quality(datasets, filters)

    st.sidebar.divider()
    st.sidebar.caption("Dashboard data is synthetic/local. Use generated screenshots only from this app.")


if __name__ == "__main__":
    main()
