# Medallion Lakehouse Analytics Engine

A production-style data lakehouse implementing the Medallion Architecture pattern (Bronze, Silver, Gold). The pipeline ingests raw transactional data, cleanses and normalizes it into a star schema, and serves executive-level insights through an interactive Streamlit dashboard powered by DuckDB.

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Data Model](#data-model-gold-layer)
- [Key Features](#key-features)
- [Repository Structure](#repository-structure)
- [Tech Stack](#tech-stack)
- [Getting Started](#getting-started)
- [License](#license)

## Architecture Overview

The pipeline follows a three-tier Medallion Architecture:

```text
  ┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
  │  Bronze Layer   │ ────► │  Silver Layer   │ ────► │   Gold Layer    │
  │  (Raw Ingest)   │       │ (Cleaned Data)  │       │  (Star Schema)  │
  └─────────────────┘       └─────────────────┘       └─────────────────┘
                                                               │
                                                               ▼
                                                     ┌──────────────────┐
                                                     │  Streamlit App   │
                                                     │  (DuckDB + UI)   │
                                                     └──────────────────┘
```

| Layer | Description |
|---|---|
| **Bronze** | Stores raw, unmodified transactional source files as ingested. |
| **Silver** | Applies cleansing, type-casting, deduplication, and null/cancellation handling. |
| **Gold** | Models business entities into fact and dimension tables (Parquet) optimized for analytical queries. |

## Data Model (Gold Layer)

| Table | Description | Key Columns |
|---|---|---|
| `fact_sales.parquet` | Transactional sales facts | `invoice_no`, `stock_code`, `customer_id`, `quantity`, `total_amount`, `invoice_timestamp` |
| `dim_customers.parquet` | Customer profile dimension | `customer_id`, `country`, `lifetime_spend`, `total_orders`, `last_order_timestamp` |
| `dim_products.parquet` | Product catalog dimension | `stock_code`, `product_name` |

## Key Features

1. **Executive KPI Dashboard** — Real-time calculation of total revenue, order volume, active customers, and average order value (AOV).
2. **RFM Customer Segmentation** — Classifies customers into behavioral cohorts (Champions, Loyal Customers, At Risk, Lost Customers) based on Recency, Frequency, and Monetary scoring.
3. **Cohort Retention Heatmap** — Computes month-over-month customer retention across an 11-month timeline using SQL window functions.
4. **Top Product Performance** — Ranks products by gross revenue and units sold.

## Repository Structure

```text
.
├── data/
│   ├── bronze/          # Raw data files
│   ├── silver/          # Cleaned intermediate files
│   └── gold/            # Final star schema Parquet files
│       ├── fact_sales.parquet
│       ├── dim_customers.parquet
│       └── dim_products.parquet
├── docs/                # Documentation screenshots
│   ├── kpi_dashboard.png
│   ├── rfm_segmentation.png
│   ├── cohort_heatmap.png
│   └── top_products.png
├── app.py               # Streamlit application
├── pipeline.py          # ETL transformation pipeline
├── requirements.txt     # Python dependencies
├── .gitignore
└── README.md
```

## Tech Stack

| Category | Technology |
|---|---|
| Storage Format | Apache Parquet |
| Query Engine | DuckDB |
| Data Pipeline | Python, Pandas, PyArrow |
| Visualization | Streamlit, Plotly Express |

## Getting Started

### Prerequisites

- Python 3.9 or higher

### Installation

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
cd YOUR_REPO_NAME

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Execution

```bash
# Step 1: Run the ETL pipeline to build the Gold layer
python pipeline.py

# Step 2: Launch the Streamlit dashboard
streamlit run app.py
```
