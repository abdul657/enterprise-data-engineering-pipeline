from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any

VALID_STATUSES = {"pending", "processing", "shipped", "cancelled"}
CENT = Decimal("0.01")


def _reject(record: dict[str, Any], reason: str) -> dict[str, Any]:
    return {"record": record, "reason": reason}


def transform_customers(
    source_rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    customers: list[dict[str, Any]] = []
    rejects: list[dict[str, Any]] = []
    seen_ids: set[int] = set()

    for row in source_rows:
        try:
            source_id = int(row["id"])
            name = str(row.get("name") or "").strip()
            email = str(row.get("email") or "").strip().lower()
            company_data = row.get("company") or {}
            company = (
                str(company_data.get("name") or "").strip()
                if isinstance(company_data, dict)
                else ""
            )

            if source_id <= 0:
                raise ValueError("customer id must be positive")
            if not name:
                raise ValueError("customer name is required")
            if source_id in seen_ids:
                raise ValueError(f"duplicate customer id: {source_id}")

            seen_ids.add(source_id)
            customers.append({
                "source_customer_id": source_id,
                "customer_name": name,
                "email": email or None,
                "company": company or None,
            })
        except (KeyError, TypeError, ValueError) as error:
            rejects.append(_reject(row, str(error)))

    return customers, rejects


def _parse_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def transform_orders(
    source_rows: list[dict[str, Any]],
    valid_customer_ids: set[int],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    orders: list[dict[str, Any]] = []
    rejects: list[dict[str, Any]] = []
    seen_ids: set[int] = set()

    for row in source_rows:
        try:
            order_id = int(row["order_id"])
            customer_id = int(row["customer_id"])
            if order_id <= 0:
                raise ValueError("order_id must be positive")
            if order_id in seen_ids:
                raise ValueError(f"duplicate order_id: {order_id}")
            seen_ids.add(order_id)

            if customer_id not in valid_customer_ids:
                raise ValueError(
                    f"customer_id {customer_id} was not found in the extracted customer source"
                )

            order_datetime = _parse_datetime(str(row["order_date"]))
            amount = Decimal(str(row["amount"]).strip()).quantize(
                CENT, rounding=ROUND_HALF_UP
            )
            if not amount.is_finite() or amount < 0:
                raise ValueError("amount must be a finite, non-negative number")

            status = str(row["status"]).strip().lower()
            if status not in VALID_STATUSES:
                raise ValueError(
                    f"status must be one of: {', '.join(sorted(VALID_STATUSES))}"
                )

            orders.append({
                "source_order_id": order_id,
                "source_customer_id": customer_id,
                "order_timestamp": order_datetime,
                "order_date": order_datetime.date(),
                "date_key": int(order_datetime.strftime("%Y%m%d")),
                "amount": amount,
                "status": status,
            })
        except (KeyError, TypeError, ValueError, InvalidOperation) as error:
            rejects.append(_reject(row, str(error)))

    return orders, rejects


def date_dimension_row(order_date: date) -> dict[str, int | date]:
    return {
        "date_key": int(order_date.strftime("%Y%m%d")),
        "calendar_date": order_date,
        "year": order_date.year,
        "quarter": (order_date.month - 1) // 3 + 1,
        "month": order_date.month,
        "day": order_date.day,
    }
