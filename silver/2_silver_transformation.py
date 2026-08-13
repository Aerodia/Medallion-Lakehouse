import os
import duckdb
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent if SCRIPT_DIR.name in ["bronze", "silver", "data"] else SCRIPT_DIR
BRONZE_PARQUET_PATH = PROJECT_ROOT / "data" / "bronze" / "online_retail_raw.parquet"
SILVER_DIR = PROJECT_ROOT / "data" / "silver"
SILVER_PARQUET_PATH = SILVER_DIR / "online_retail_silver.parquet"

def transform_bronze_to_silver():
    """Reads raw Bronze Parquet, applies data cleaning using DuckDB, and saves to Silver Parquet."""
    os.makedirs(SILVER_DIR, exist_ok=True)
    
    if not BRONZE_PARQUET_PATH.exists():
        print(f"Error: Raw Bronze file not found at {BRONZE_PARQUET_PATH}")
        print("Please run Phase 1 (1_bronze_ingestion.py) first.")
        return

    print("Starting Phase 2: Cleaning Bronze data with DuckDB...")
    con = duckdb.connect()
    silver_query = f"""
    CREATE TABLE silver_orders AS
    SELECT
        CAST(InvoiceNo AS VARCHAR) AS invoice_no,
        CAST(StockCode AS VARCHAR) AS stock_code,
        TRIM(UPPER(CAST(Description AS VARCHAR))) AS product_description,
        CAST(Quantity AS INT) AS quantity,
        CAST(InvoiceDate AS TIMESTAMP) AS invoice_timestamp,
        CAST(UnitPrice AS DOUBLE) AS unit_price,
        ROUND(CAST(Quantity * UnitPrice AS DOUBLE), 2) AS total_amount,
        CAST(CustomerID AS INT) AS customer_id,
        TRIM(Country) AS country,
        
        -- Flag cancellations and returned orders
        CASE 
            WHEN InvoiceNo LIKE 'C%' OR Quantity < 0 THEN TRUE 
            ELSE FALSE 
        END AS is_cancellation
        
    FROM read_parquet('{BRONZE_PARQUET_PATH}')
    WHERE CustomerID IS NOT NULL
      AND UnitPrice > 0;

    -- Write cleaned table to Silver Parquet file
    COPY silver_orders TO '{SILVER_PARQUET_PATH}' (FORMAT PARQUET);
    """
    con.execute(silver_query)
    raw_count = con.execute(f"SELECT COUNT(*) FROM read_parquet('{BRONZE_PARQUET_PATH}')").fetchone()[0]
    silver_count = con.execute(f"SELECT COUNT(*) FROM read_parquet('{SILVER_PARQUET_PATH}')").fetchone()[0]
    dropped_count = raw_count - silver_count

    print(f"Success! Silver Parquet saved to:\n   {SILVER_PARQUET_PATH}")
    print(f"Raw Bronze Records : {raw_count:,}")
    print(f"Clean Silver Records: {silver_count:,}")
    print(f"Dropped Records     : {dropped_count:,} (Missing Customer IDs, $0 test items)")

if __name__ == "__main__":
    transform_bronze_to_silver()