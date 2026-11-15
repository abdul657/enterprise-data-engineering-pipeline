from __future__ import annotations

from typing import Any
from psycopg import Connection

from .transform import date_dimension_row


def initialize_warehouse(conn: Connection[Any], schema_path: str = "sql/schema.sql") -> None:
    """Create warehouse tables and indexes if they do not exist."""
    conn.execute(open(schema_path, encoding="utf-8").read())


def load_warehouse(
    conn: Connection[Any],
    customers: list[dict[str, Any]],
    orders: list[dict[str, Any]],
) -> tuple[int, int]:
    """Upsert dimensions first, then facts; caller controls the transaction."""
    customer_keys: dict[int, int] = {}

    for customer in customers:
        row = conn.execute(
            """
            INSERT INTO dim_customer
                (source_customer_id, customer_name, email, company, updated_at)
            VALUES (%s, %s, %s, %s, NOW())
            ON CONFLICT (source_customer_id) DO UPDATE SET
                customer_name = EXCLUDED.customer_name,
                email = EXCLUDED.email,
                company = EXCLUDED.company,
                updated_at = NOW()
            RETURNING customer_key, source_customer_id
            """,
            (
                customer["source_customer_id"],
                customer["customer_name"],
                customer["email"],
                customer["company"],
            ),
        ).fetchone()
        customer_keys[int(row[1])] = int(row[0])

    date_keys: dict[int, int] = {}
    for order in orders:
        date_row = date_dimension_row(order["order_date"])
        row = conn.execute(
            """
            INSERT INTO dim_date
                (date_key, calendar_date, calendar_year, calendar_quarter,
                 calendar_month, calendar_day)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (date_key) DO UPDATE SET
                calendar_date = EXCLUDED.calendar_date,
                calendar_year = EXCLUDED.calendar_year,
                calendar_quarter = EXCLUDED.calendar_quarter,
                calendar_month = EXCLUDED.calendar_month,
                calendar_day = EXCLUDED.calendar_day
            RETURNING date_key
            """,
            (
                date_row["date_key"],
                date_row["calendar_date"],
                date_row["year"],
                date_row["quarter"],
                date_row["month"],
                date_row["day"],
            ),
        ).fetchone()
        date_keys[int(order["date_key"])] = int(row[0])

    for order in orders:
        conn.execute(
            """
            INSERT INTO fact_order
                (source_order_id, customer_key, date_key, order_timestamp, amount, status)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (source_order_id) DO UPDATE SET
                customer_key = EXCLUDED.customer_key,
                date_key = EXCLUDED.date_key,
                order_timestamp = EXCLUDED.order_timestamp,
                amount = EXCLUDED.amount,
                status = EXCLUDED.status,
                loaded_at = NOW()
            """,
            (
                order["source_order_id"],
                customer_keys[order["source_customer_id"]],
                date_keys[order["date_key"]],
                order["order_timestamp"],
                order["amount"],
                order["status"],
            ),
        )

    return len(customers), len(orders)
