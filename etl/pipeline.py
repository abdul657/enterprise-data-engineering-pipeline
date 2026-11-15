from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4

import psycopg

from .config import Settings, load_settings
from .extract import extract_customers, extract_orders
from .load import initialize_warehouse, load_warehouse
from .storage import copy_source_file, upload_to_s3, write_json
from .transform import transform_customers, transform_orders


def run_pipeline(settings: Settings | None = None) -> dict[str, object]:
    settings = settings or load_settings()
    run_id = uuid4()
    started_at = datetime.now(timezone.utc)
    settings.raw_data_dir.mkdir(parents=True, exist_ok=True)
    settings.rejects_dir.mkdir(parents=True, exist_ok=True)

    with psycopg.connect(settings.database_url) as conn:
        initialize_warehouse(conn)
        conn.commit()
        conn.execute(
            "INSERT INTO etl_runs (run_id, status, started_at) VALUES (%s, 'running', %s)",
            (run_id, started_at),
        )
        conn.commit()

        try:
            source_customers = extract_customers(
                settings.customers_api_url, settings.http_timeout_seconds
            )
            source_orders = extract_orders(settings.orders_csv_path)

            raw_customers_path = write_json(
                settings.raw_data_dir, f"{run_id}_customers.json", source_customers
            )
            raw_orders_path = copy_source_file(
                settings.orders_csv_path, settings.raw_data_dir, f"{run_id}_orders.csv"
            )

            customers, customer_rejects = transform_customers(source_customers)
            orders, order_rejects = transform_orders(
                source_orders,
                {customer["source_customer_id"] for customer in customers},
            )
            rejects = [
                *({"entity": "customer", **item} for item in customer_rejects),
                *({"entity": "order", **item} for item in order_rejects),
            ]
            rejects_path = write_json(
                settings.rejects_dir, f"{run_id}_rejects.json", rejects
            )

            archived_to = upload_to_s3(
                [raw_customers_path, raw_orders_path, rejects_path],
                settings.aws_s3_bucket or "",
                settings.aws_region,
                run_id,
            )

            with conn.transaction():
                customers_loaded, orders_loaded = load_warehouse(conn, customers, orders)
                completed_at = datetime.now(timezone.utc)
                conn.execute(
                    """
                    UPDATE etl_runs
                    SET status = 'succeeded',
                        completed_at = %s,
                        customers_extracted = %s,
                        orders_extracted = %s,
                        customers_loaded = %s,
                        orders_loaded = %s,
                        rejected_records = %s
                    WHERE run_id = %s
                    """,
                    (
                        completed_at,
                        len(source_customers),
                        len(source_orders),
                        customers_loaded,
                        orders_loaded,
                        len(rejects),
                        run_id,
                    ),
                )

            return {
                "run_id": str(run_id),
                "status": "succeeded",
                "customers_extracted": len(source_customers),
                "orders_extracted": len(source_orders),
                "customers_loaded": customers_loaded,
                "orders_loaded": orders_loaded,
                "rejected_records": len(rejects),
                "s3_archives": archived_to,
                "rejects_file": str(rejects_path),
            }
        except Exception as error:
            with conn.transaction():
                conn.execute(
                    """
                    UPDATE etl_runs
                    SET status = 'failed', completed_at = %s, error_message = %s
                    WHERE run_id = %s
                    """,
                    (datetime.now(timezone.utc), str(error)[:4000], run_id),
                )
            raise


def main() -> None:
    result = run_pipeline()
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
