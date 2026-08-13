import streamlit as st
import duckdb
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path

# Page Configuration
st.set_page_config(
    page_title="Medallion Lakehouse Analytics",
    layout="wide"
)

# Resolve Paths
SCRIPT_DIR = Path(__file__).resolve().parent
GOLD_DIR = SCRIPT_DIR / "data" / "gold"
FACT_PARQUET = GOLD_DIR / "fact_sales.parquet"
CUST_PARQUET = GOLD_DIR / "dim_customers.parquet"
PROD_PARQUET = GOLD_DIR / "dim_products.parquet"


def check_data_files():
    """Verify Gold Parquet files exist before running queries."""
    missing = []
    for path, name in [(FACT_PARQUET, "fact_sales"), (CUST_PARQUET, "dim_customers"), (PROD_PARQUET, "dim_products")]:
        if not path.exists():
            missing.append(name)
    return missing


# Cached Data Loaders
@st.cache_data
def get_kpis():
    con = duckdb.connect()
    query = f"""
    SELECT 
        ROUND(SUM(total_amount), 2) AS total_revenue,
        COUNT(DISTINCT invoice_no) AS total_orders,
        COUNT(DISTINCT customer_id) AS active_customers,
        ROUND(SUM(total_amount) / COUNT(DISTINCT invoice_no), 2) AS avg_order_value
    FROM read_parquet('{FACT_PARQUET}')
    """
    return con.execute(query).fetchdf()


@st.cache_data
def get_rfm_data():
    con = duckdb.connect()
    query = f"""
    WITH snapshot_date AS (
        SELECT MAX(invoice_timestamp) + INTERVAL 1 DAY AS max_date 
        FROM read_parquet('{FACT_PARQUET}')
    ),
    raw_rfm AS (
        SELECT 
            c.customer_id,
            c.country,
            DATE_DIFF('day', c.last_order_timestamp, s.max_date) AS recency_days,
            c.total_orders AS frequency,
            c.lifetime_spend AS monetary
        FROM read_parquet('{CUST_PARQUET}') c
        CROSS JOIN snapshot_date s
        WHERE c.lifetime_spend > 0
    ),
    rfm_scores AS (
        SELECT 
            customer_id,
            country,
            recency_days,
            frequency,
            monetary,
            NTILE(5) OVER (ORDER BY recency_days DESC) AS r_score,
            NTILE(5) OVER (ORDER BY frequency ASC) AS f_score,
            NTILE(5) OVER (ORDER BY monetary ASC) AS m_score
        FROM raw_rfm
    )
    SELECT *,
        CASE 
            WHEN r_score >= 4 AND f_score >= 4 THEN 'Champions'
            WHEN r_score >= 3 AND f_score >= 3 THEN 'Loyal Customers'
            WHEN r_score <= 2 AND f_score >= 3 THEN 'At Risk'
            WHEN r_score <= 2 AND f_score <= 2 THEN 'Lost Customers'
            ELSE 'Standard Buyers'
        END AS customer_segment
    FROM rfm_scores
    """
    return con.execute(query).fetchdf()


@st.cache_data
def get_cohort_matrix():
    con = duckdb.connect()
    query = f"""
    WITH first_purchase AS (
        SELECT 
            customer_id,
            DATE_TRUNC('month', MIN(invoice_timestamp)) AS cohort_month
        FROM read_parquet('{FACT_PARQUET}')
        GROUP BY customer_id
    ),
    user_activity AS (
        SELECT DISTINCT
            f.customer_id,
            fp.cohort_month,
            DATE_TRUNC('month', f.invoice_timestamp) AS activity_month,
            (EXTRACT(YEAR FROM f.invoice_timestamp) - EXTRACT(YEAR FROM fp.cohort_month)) * 12 +
            (EXTRACT(MONTH FROM f.invoice_timestamp) - EXTRACT(MONTH FROM fp.cohort_month)) AS month_number
        FROM read_parquet('{FACT_PARQUET}') f
        JOIN first_purchase fp ON f.customer_id = fp.customer_id
    ),
    cohort_counts AS (
        SELECT 
            STRFTIME(cohort_month, '%Y-%m') AS cohort,
            month_number,
            COUNT(DISTINCT customer_id) AS active_users
        FROM user_activity
        WHERE month_number <= 11
        GROUP BY cohort_month, month_number
    ),
    cohort_sizes AS (
        SELECT cohort, active_users AS initial_users
        FROM cohort_counts
        WHERE month_number = 0
    )
    SELECT 
        cc.cohort,
        cc.month_number,
        ROUND(cc.active_users * 100.0 / cs.initial_users, 1) AS retention_rate
    FROM cohort_counts cc
    JOIN cohort_sizes cs ON cc.cohort = cs.cohort
    ORDER BY cc.cohort, cc.month_number
    """
    df = con.execute(query).fetchdf()
    pivot_df = df.pivot(index="cohort", columns="month_number", values="retention_rate")
    return pivot_df


@st.cache_data
def get_top_products():
    con = duckdb.connect()
    query = f"""
    SELECT 
        p.product_name,
        SUM(f.quantity) AS units_sold,
        ROUND(SUM(f.total_amount), 2) AS total_revenue
    FROM read_parquet('{FACT_PARQUET}') f
    JOIN read_parquet('{PROD_PARQUET}') p ON f.stock_code = p.stock_code
    GROUP BY p.product_name
    ORDER BY total_revenue DESC
    LIMIT 10
    """
    return con.execute(query).fetchdf()


# Main Application Layout
def main():
    st.title("Gold Layer Data Lakehouse Analytics")
    st.markdown("Executive Business Intelligence built on top of DuckDB and Parquet Star Schema.")
    st.divider()

    missing_files = check_data_files()
    if missing_files:
        st.error(f"Missing Gold Parquet files: {', '.join(missing_files)}. Run your pipeline runner.py first.")
        st.stop()

    # Section 1: KPI Metrics Row
    df_kpi = get_kpis()
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="Total Revenue",
            value=f"${df_kpi['total_revenue'][0]:,.2f}"
        )
    with col2:
        st.metric(
            label="Total Orders",
            value=f"{df_kpi['total_orders'][0]:,}"
        )
    with col3:
        st.metric(
            label="Active Customers",
            value=f"{df_kpi['active_customers'][0]:,}"
        )
    with col4:
        st.metric(
            label="Average Order Value",
            value=f"${df_kpi['avg_order_value'][0]:,.2f}"
        )

    st.divider()

    # Section 2: Analytics Tabs
    tab1, tab2, tab3 = st.tabs(["RFM Segmentation", "Cohort Retention Matrix", "Top Products"])

    # TAB 1: RFM Customer Segmentation
    with tab1:
        st.subheader("RFM Customer Segmentation Analysis")
        df_rfm = get_rfm_data()

        col_left, col_right = st.columns([2, 1])

        with col_left:
            fig_scatter = px.scatter(
                df_rfm,
                x="recency_days",
                y="monetary",
                color="customer_segment",
                size="frequency",
                hover_data=["customer_id", "country"],
                log_y=True,
                labels={
                    "recency_days": "Recency (Days Since Last Order)",
                    "monetary": "Lifetime Spend ($ Log Scale)",
                    "customer_segment": "Segment"
                },
                title="Customer Distribution: Recency vs Spend",
                template="plotly_white"
            )
            st.plotly_chart(fig_scatter, use_container_width=True)

        with col_right:
            df_summary = (
                df_rfm.groupby("customer_segment")
                .agg(
                    total_customers=("customer_id", "count"),
                    avg_spend=("monetary", "mean"),
                    total_revenue=("monetary", "sum")
                )
                .reset_index()
                .sort_values(by="total_revenue", ascending=False)
            )

            fig_bar = px.bar(
                df_summary,
                x="total_revenue",
                y="customer_segment",
                orientation="h",
                color="customer_segment",
                labels={"total_revenue": "Total Revenue ($)", "customer_segment": "Segment"},
                title="Revenue Contribution by Segment",
                template="plotly_white"
            )
            fig_bar.update_layout(showlegend=False)
            st.plotly_chart(fig_bar, use_container_width=True)

        st.dataframe(
            df_summary.style.format({
                "avg_spend": "${:,.2f}",
                "total_revenue": "${:,.2f}",
                "total_customers": "{:,}"
            }),
            use_container_width=True
        )

    # TAB 2: Cohort Retention Matrix
    with tab2:
        st.subheader("Monthly Cohort Retention Heatmap")
        pivot_cohort = get_cohort_matrix()

        pivot_cohort.columns = [f"M+{col}" for col in pivot_cohort.columns]

        fig_heatmap = px.imshow(
            pivot_cohort,
            labels=dict(x="Months Since First Order", y="Cohort Month", color="Retention %"),
            x=pivot_cohort.columns,
            y=pivot_cohort.index,
            text_auto=True,
            color_continuous_scale="Blues",
            aspect="auto",
            title="Customer Retention Rate (%) by Monthly Cohort"
        )
        fig_heatmap.update_xaxes(side="top")
        st.plotly_chart(fig_heatmap, use_container_width=True)

    # TAB 3: Top Products
    with tab3:
        st.subheader("Top 10 Products by Gross Revenue")
        df_prod = get_top_products()

        fig_prod = px.bar(
            df_prod,
            x="total_revenue",
            y="product_name",
            orientation="h",
            labels={"total_revenue": "Gross Revenue ($)", "product_name": "Product Name"},
            template="plotly_white",
            color="total_revenue",
            color_continuous_scale="Viridis"
        )
        fig_prod.update_layout(yaxis=dict(autorange="reversed"), showlegend=False)
        st.plotly_chart(fig_prod, use_container_width=True)

        st.dataframe(
            df_prod.style.format({
                "total_revenue": "${:,.2f}",
                "units_sold": "{:,}"
            }),
            use_container_width=True
        )


if __name__ == "__main__":
    main()