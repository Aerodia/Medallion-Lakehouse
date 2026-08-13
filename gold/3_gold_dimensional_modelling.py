import os
import duckdb
from pathlib import Path

# Dynamically resolve project directory
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent if SCRIPT_DIR.name in ["bronze", "silver", "gold", "data"] else SCRIPT_DIR

# Define input and output paths
SILVER_PARQUET_PATH = PROJECT_ROOT / "data" / "silver" / "online_retail_silver.parquet"
GOLD_DIR = PROJECT_ROOT / "data" / "gold"

def build_gold_layer():
    """Reads Silver Parquet and builds Star Schema dimension & fact tables in Gold Parquet format."""
    
    os.makedirs(GOLD_DIR, exist_ok=True)
    
    if not SILVER_PARQUET_PATH.exists():
        print(f"Error: Silver file not found at {SILVER_PARQUET_PATH}")
        print("Please run Phase 2 (2_silver_transformation.py) first.")
        return

    print("🌟 Starting Phase 3: Building Gold Layer Star Schema...")
    con = duckdb.connect()
    dim_customers_path = GOLD_DIR / "dim_customers.parquet"
    print(" └─ Modeling dim_customers...")
    
    con.execute(f"""
    COPY (
        SELECT
            customer_id,
            MODE(country) AS country, -- Most frequent country
            MIN(invoice_timestamp) AS first_order_timestamp,
            MAX(invoice_timestamp) AS last_order_timestamp,
            COUNT(DISTINCT invoice_no) AS total_orders,
            ROUND(SUM(CASE WHEN NOT is_cancellation THEN total_amount ELSE 0 END), 2) AS lifetime_spend
        FROM read_parquet('{SILVER_PARQUET_PATH}')
        GROUP BY customer_id
    ) TO '{dim_customers_path}' (FORMAT PARQUET);
    """)
    dim_products_path = GOLD_DIR / "dim_products.parquet"
    print(" └─ Modeling dim_products...")
    
    con.execute(f"""
    COPY (
        SELECT
            stock_code,
            MODE(product_description) AS product_name,
            ROUND(AVG(unit_price), 2) AS avg_unit_price
        FROM read_parquet('{SILVER_PARQUET_PATH}')
        GROUP BY stock_code
    ) TO '{dim_products_path}' (FORMAT PARQUET);
    """)

    fact_sales_path = GOLD_DIR / "fact_sales.parquet"
    print(" └─ Modeling fact_sales...")
    
    con.execute(f"""
    COPY (
        SELECT
            invoice_no,
            customer_id,
            stock_code,
            invoice_timestamp,
            quantity,
            unit_price,
            total_amount,
            is_cancellation
        FROM read_parquet('{SILVER_PARQUET_PATH}')
    ) TO '{fact_sales_path}' (FORMAT PARQUET);
    """)

    # Validate output counts
    cust_count = con.execute(f"SELECT COUNT(*) FROM read_parquet('{dim_customers_path}')").fetchone()[0]
    prod_count = con.execute(f"SELECT COUNT(*) FROM read_parquet('{dim_products_path}')").fetchone()[0]
    fact_count = con.execute(f"SELECT COUNT(*) FROM read_parquet('{fact_sales_path}')").fetchone()[0]

    print("\n Success! Gold Layer complete:")
    print(f"dim_customers : {cust_count:,} unique customers")
    print(f"dim_products  : {prod_count:,} unique products")
    print(f"fact_sales    : {fact_count:,} transaction line items")

if __name__ == "__main__":
    build_gold_layer()