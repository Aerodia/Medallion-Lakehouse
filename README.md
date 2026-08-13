# Medallion Lakehouse Analytics Engine

A production-style data lakehouse implementing the Medallion Architecture pattern (Bronze, Silver, Gold). The pipeline ingests raw transactional data, cleanses and normalizes it into a star schema, and serves executive-level insights through an interactive Streamlit dashboard powered by DuckDB.

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Data Model](#data-model-gold-layer)
- [Key Features](#key-features)
- [Repository Structure](#repository-structure)
- [Tech Stack](#tech-stack)
- [Getting Started](#getting-started)

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
├── bronze/                    # Raw ingested source files
├── silver/                    # Cleaned, deduplicated intermediate data
├── gold/                      # Final star schema (fact/dimension Parquet files)
├── data/                      # Source input data
├── runner.py                  # Orchestrates the Bronze → Silver → Gold pipeline
├── 4_analytics_and_rfm.py     # Analytics logic: KPIs, RFM segmentation, cohort retention
├── app.py                     # Streamlit dashboard application
└── README.md                  # Project documentation
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
git clone https://github.com/Aerodia/Medallion-Lakehouse.git
cd Medallion-Lakehouse

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install pandas pyarrow duckdb streamlit plotly
```

### Execution

```bash
# Step 1: Run the pipeline to build the Bronze, Silver, and Gold layers
python runner.py

# Step 2: Run analytics and RFM segmentation
python 4_analytics_and_rfm.py

# Step 3: Launch the Streamlit dashboard
streamlit run app.py
```
