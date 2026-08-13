import duckdb
from pathlib import Path

# Resolve project root
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent if SCRIPT_DIR.name in ["bronze", "silver", "gold", "data"] else SCRIPT_DIR

GOLD_DIR = PROJECT_ROOT / "data" / "gold"
CUST_PARQUET = GOLD_DIR / "dim_customers.parquet"
FACT_PARQUET = GOLD_DIR / "fact_sales.parquet"

def run_rfm_analysis():
    """Calculates RFM metrics & assigns customer segments using SQL quantiles."""
    print("Executing RFM Customer Segmentation Query...\n")
    con = duckdb.connect()

    rfm_query = f"""
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
    ),
    segmented AS (
        SELECT *,
            CASE 
                WHEN r_score >= 4 AND f_score >= 4 THEN 'Champions'
                WHEN r_score >= 3 AND f_score >= 3 THEN 'Loyal Customers'
                WHEN r_score <= 2 AND f_score >= 3 THEN 'At Risk'
                WHEN r_score <= 2 AND f_score <= 2 THEN 'Lost Customers'
                ELSE 'Standard Buyers 🛒'
            END AS customer_segment
        FROM rfm_scores
    )
    SELECT 
        customer_segment,
        COUNT(customer_id) AS total_customers,
        ROUND(AVG(recency_days), 1) AS avg_recency_days,
        ROUND(AVG(frequency), 1) AS avg_orders,
        ROUND(AVG(monetary), 2) AS avg_lifetime_spend,
        ROUND(SUM(monetary), 2) AS total_revenue
    FROM segmented
    GROUP BY customer_segment
    ORDER BY total_revenue DESC;
    """

    df_rfm = con.execute(rfm_query).fetchdf()
    print(df_rfm.to_string(index=False))

def run_cohort_retention():
    """Computes month-over-month cohort retention rates."""
    print("\n\n Executing Monthly Cohort Retention Query (First 6 Cohorts)...\n")
    con = duckdb.connect()

    cohort_query = f"""
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
    )
    SELECT 
        STRFTIME(cohort_month, '%Y-%m') AS cohort,
        COUNT(DISTINCT CASE WHEN month_number = 0 THEN customer_id END) AS m0_users,
        COUNT(DISTINCT CASE WHEN month_number = 1 THEN customer_id END) AS m1_users,
        COUNT(DISTINCT CASE WHEN month_number = 2 THEN customer_id END) AS m2_users,
        COUNT(DISTINCT CASE WHEN month_number = 3 THEN customer_id END) AS m3_users,
        ROUND(COUNT(DISTINCT CASE WHEN month_number = 1 THEN customer_id END) * 100.0 / 
              COUNT(DISTINCT CASE WHEN month_number = 0 THEN customer_id END), 1) || '%' AS m1_retention_rate
    FROM user_activity
    GROUP BY cohort_month
    ORDER BY cohort_month
    LIMIT 6;
    """

    df_cohort = con.execute(cohort_query).fetchdf()
    print(df_cohort.to_string(index=False))

if __name__ == "__main__":
    run_rfm_analysis()
    run_cohort_retention()