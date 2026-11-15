from __future__ import annotations

import os
from datetime import date, datetime, timezone
from decimal import Decimal

import psycopg
import pytest

from etl.load import initialize_warehouse, load_warehouse


@pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"),
    reason="Set TEST_DATABASE_URL to run PostgreSQL integration tests",
)
def test_warehouse_upserts_are_idempotent():
    database_url = os.environ["TEST_DATABASE_URL"]

    customer = {
        "source_customer_id": 501,
        "customer_name": "Integration Test Customer",
        "email": "integration@example.test",
        "company": "Test Co",
    }
    order = {
        "source_order_id": 90001,
        "source_customer_id": 501,
        "order_timestamp": datetime(2026, 10, 1, 12, 0, tzinfo=timezone.utc),
        "order_date": date(2026, 10, 1),
        "date_key": 20261001,
        "amount": Decimal("100.00"),
        "status": "pending",
    }

    with psycopg.connect(database_url) as conn:
        initialize_warehouse(conn)
        with conn.transaction():
            conn.execute(
                "TRUNCATE TABLE fact_order, dim_date, dim_customer RESTART IDENTITY CASCADE"
            )
            assert load_warehouse(conn, [customer], [order]) == (1, 1)

        updated_order = {**order, "amount": Decimal("125.50"), "status": "shipped"}
        with conn.transaction():
            assert load_warehouse(conn, [customer], [updated_order]) == (1, 1)

        fact_count = conn.execute(
            "SELECT COUNT(*) FROM fact_order WHERE source_order_id = %s",
            (order["source_order_id"],),
        ).fetchone()[0]
        customer_count = conn.execute(
            "SELECT COUNT(*) FROM dim_customer WHERE source_customer_id = %s",
            (customer["source_customer_id"],),
        ).fetchone()[0]
        fact = conn.execute(
            "SELECT amount, status FROM fact_order WHERE source_order_id = %s",
            (order["source_order_id"],),
        ).fetchone()

    assert fact_count == 1
    assert customer_count == 1
    assert fact == (Decimal("125.50"), "shipped")
