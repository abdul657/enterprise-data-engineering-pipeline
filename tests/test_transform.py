from datetime import date
from decimal import Decimal

from etl.transform import date_dimension_row, transform_customers, transform_orders


def sample_customers():
    return [
        {
            "id": 1,
            "name": "  Alex Example ",
            "email": "ALEX@EXAMPLE.COM",
            "company": {"name": "Example Co"},
        },
        {"id": 2, "name": "Jordan Sample", "email": None, "company": {}},
    ]


def test_customer_transform_normalizes_fields():
    customers, rejects = transform_customers(sample_customers())

    assert rejects == []
    assert customers[0] == {
        "source_customer_id": 1,
        "customer_name": "Alex Example",
        "email": "alex@example.com",
        "company": "Example Co",
    }
    assert customers[1]["email"] is None


def test_customer_transform_rejects_missing_names_and_duplicate_ids():
    customers, rejects = transform_customers([
        {"id": 1, "name": "First"},
        {"id": 1, "name": "Duplicate"},
        {"id": 3, "name": "  "},
    ])

    assert len(customers) == 1
    assert len(rejects) == 2
    assert "duplicate customer id" in rejects[0]["reason"]
    assert "customer name is required" in rejects[1]["reason"]


def test_order_transform_parses_amount_date_and_status():
    rows, rejects = transform_orders([
        {
            "order_id": "1001",
            "customer_id": "1",
            "order_date": "2026-10-01T09:15:00Z",
            "amount": "125.5",
            "status": " PENDING ",
        }
    ], {1})

    assert rejects == []
    assert rows[0]["amount"] == Decimal("125.50")
    assert rows[0]["order_date"] == date(2026, 10, 1)
    assert rows[0]["date_key"] == 20261001
    assert rows[0]["status"] == "pending"


def test_order_transform_rejects_unknown_customer_bad_status_and_duplicate_id():
    source = {
        "order_id": "1001",
        "customer_id": "99",
        "order_date": "2026-10-01T09:15:00Z",
        "amount": "20.00",
        "status": "pending",
    }
    rows, rejects = transform_orders([
        source,
        {**source, "order_id": "1002", "customer_id": "1", "status": "lost"},
        {**source, "customer_id": "1"},
    ], {1})

    assert rows == []
    assert len(rejects) == 3
    assert "was not found" in rejects[0]["reason"]
    assert "status must be one of" in rejects[1]["reason"]
    assert "duplicate order_id" in rejects[2]["reason"]


def test_order_transform_rejects_invalid_amount_and_date():
    rows, rejects = transform_orders([
        {"order_id": "1", "customer_id": "1", "order_date": "not-a-date", "amount": "2", "status": "pending"},
        {"order_id": "2", "customer_id": "1", "order_date": "2026-10-01", "amount": "-1", "status": "pending"},
    ], {1})

    assert rows == []
    assert len(rejects) == 2


def test_date_dimension_derives_calendar_attributes():
    assert date_dimension_row(date(2026, 11, 15)) == {
        "date_key": 20261115,
        "calendar_date": date(2026, 11, 15),
        "year": 2026,
        "quarter": 4,
        "month": 11,
        "day": 15,
    }
