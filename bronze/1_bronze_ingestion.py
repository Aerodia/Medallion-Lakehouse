import os
import requests
import pandas as pd
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent if SCRIPT_DIR.name in ["bronze", "data"] else SCRIPT_DIR
BRONZE_DIR = PROJECT_ROOT / "data" / "bronze"
RAW_EXCEL_PATH = BRONZE_DIR / "Online_Retail.xlsx"
BRONZE_PARQUET_PATH = BRONZE_DIR / "online_retail_raw.parquet"

DATASET_URL = "https://archive.ics.uci.edu/ml/machine-learning-databases/00352/Online%20Retail.xlsx"

def download_raw_data():
    """Downloads the raw excel file from UCI Archive if not present."""
    os.makedirs(BRONZE_DIR, exist_ok=True)
    
    if not RAW_EXCEL_PATH.exists():
        print(f"Downloading UCI Online Retail Dataset (~23 MB) to:\n   {BRONZE_DIR} ...")
        response = requests.get(DATASET_URL, stream=True)
        response.raise_for_status()
        
        with open(RAW_EXCEL_PATH, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        print("Download completed successfully!")
    else:
        print("Raw Excel dataset already downloaded locally.")

def save_to_bronze_parquet():
    """Converts the raw excel into a lossless Bronze Parquet file."""
    print("Loading Excel file into memory (this may take 15-30 seconds)...")
    df_raw = pd.read_excel(
        RAW_EXCEL_PATH,
        dtype={
            'InvoiceNo': str,
            'StockCode': str,
            'Description': str
        }
    )
    
    print(f"Dataset Shape: {df_raw.shape[0]:,} rows x {df_raw.shape[1]} columns")
    print(f"Writing raw data to Bronze Layer:\n   {BRONZE_PARQUET_PATH} ...")
    
    df_raw.to_parquet(BRONZE_PARQUET_PATH, index=False)
    
    excel_size = os.path.getsize(RAW_EXCEL_PATH) / (1024 * 1024)
    parquet_size = os.path.getsize(BRONZE_PARQUET_PATH) / (1024 * 1024)
    
    print(f"✨ Success! Bronze file saved.")
    print(f"📦 Compression efficiency: Raw Excel ({excel_size:.2f} MB) ➔ Parquet ({parquet_size:.2f} MB)")

if __name__ == "__main__":
    download_raw_data()
    save_to_bronze_parquet()