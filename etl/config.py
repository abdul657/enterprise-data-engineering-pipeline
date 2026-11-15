from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    database_url: str
    customers_api_url: str
    orders_csv_path: Path
    raw_data_dir: Path
    rejects_dir: Path
    aws_s3_bucket: str | None
    aws_region: str
    http_timeout_seconds: float


def load_settings() -> Settings:
    load_dotenv()
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        raise ValueError("DATABASE_URL must be set before running the ETL pipeline")

    return Settings(
        database_url=database_url,
        customers_api_url=os.getenv(
            "CUSTOMERS_API_URL", "https://jsonplaceholder.typicode.com/users"
        ),
        orders_csv_path=Path(os.getenv("ORDERS_CSV_PATH", "data/source/orders.csv")),
        raw_data_dir=Path(os.getenv("RAW_DATA_DIR", "data/raw")),
        rejects_dir=Path(os.getenv("REJECTS_DIR", "data/rejects")),
        aws_s3_bucket=os.getenv("AWS_S3_BUCKET") or None,
        aws_region=os.getenv("AWS_REGION", "us-east-1"),
        http_timeout_seconds=float(os.getenv("ETL_HTTP_TIMEOUT_SECONDS", "20")),
    )
