from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

import httpx


def extract_customers(api_url: str, timeout_seconds: float) -> list[dict[str, Any]]:
    """Fetch source customers from a REST endpoint and validate the top-level shape."""
    response = httpx.get(api_url, timeout=timeout_seconds)
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, list) or not all(isinstance(row, dict) for row in payload):
        raise ValueError("Customer API must return a JSON array of objects")
    return payload


def extract_orders(csv_path: Path) -> list[dict[str, str]]:
    """Read order source rows from CSV without applying business transformations."""
    if not csv_path.is_file():
        raise FileNotFoundError(f"Orders source CSV does not exist: {csv_path}")
    with csv_path.open("r", encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        required = {"order_id", "customer_id", "order_date", "amount", "status"}
        missing = required.difference(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Orders CSV is missing required columns: {', '.join(sorted(missing))}")
        return [dict(row) for row in reader]
