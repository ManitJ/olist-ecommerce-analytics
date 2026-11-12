"""Central paths and constants. All paths are resolved relative to the repo root."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_RAW = ROOT / "data" / "raw"
DATA_PROCESSED = ROOT / "data" / "processed"
DATA_BI = ROOT / "data" / "bi"
SQL_DIR = ROOT / "sql"
ASSETS = ROOT / "assets" / "charts"
OUTPUTS = ROOT / "outputs"
DUCKDB_PATH = DATA_PROCESSED / "olist.duckdb"

KAGGLE_URL = "https://www.kaggle.com/api/v1/datasets/download/olistbr/brazilian-ecommerce"
DATASET_PAGE = "https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce"

RAW_FILES = {
    "customers": "olist_customers_dataset.csv",
    "geolocation": "olist_geolocation_dataset.csv",
    "order_items": "olist_order_items_dataset.csv",
    "payments": "olist_order_payments_dataset.csv",
    "reviews": "olist_order_reviews_dataset.csv",
    "orders": "olist_orders_dataset.csv",
    "products": "olist_products_dataset.csv",
    "sellers": "olist_sellers_dataset.csv",
    "category_translation": "product_category_name_translation.csv",
}
