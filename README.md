# Enterprise Data Engineering Pipeline

A reproducible Python ETL project that ingests customer records from a REST API and order records from CSV, validates and transforms the data, lands raw extracts, and loads analytics-ready tables into PostgreSQL.

## What it demonstrates

- **Extract:** Retrieve customer records from JSONPlaceholder and read source orders from CSV.
- **Raw data lake:** Persist unmodified API responses and source CSV snapshots locally under `data/raw/`.
- **Transform:** Normalize customer and order fields, parse timestamps and monetary values, and derive date attributes.
- **Data quality:** Validate required fields, customer references, order statuses, amount bounds, and duplicate source IDs. Invalid rows are written to a rejects file with reasons.
- **Warehouse:** Load a star schema with `dim_customer`, `dim_date`, and `fact_order`; PostgreSQL upserts make repeat runs idempotent by source order ID.
- **Run observability:** Record run status, start/end times, and extracted/loaded/rejected row counts in `etl_runs`.
- **Cloud option:** Optionally upload raw extracts and reject files to an S3 bucket using boto3's standard credential chain.
- **Engineering practices:** Typed Python modules, environment-based configuration, Docker Compose, pytest, and GitHub Actions.

## Architecture

```text
JSONPlaceholder API         orders.csv
        |                       |
        v                       v
     Extractors (HTTP + CSV)
                |
                v
      Raw landing (data/raw/)
                |
                v
      Transform + data quality
          |             |
          v             v
    Valid records    Rejects + reasons
          |
          v
    PostgreSQL warehouse
    - dim_customer
    - dim_date
    - fact_order
    - etl_runs
          |
          v
    Analytics SQL / BI tools

Optional: raw extracts and rejects -> AWS S3
```

## Quick start (Docker)

Requirements: Docker Desktop with Compose.

```bash
git clone https://github.com/abdul657/enterprise-data-engineering-pipeline.git
cd enterprise-data-engineering-pipeline
cp .env.example .env
docker compose up --build
```

The pipeline container waits for PostgreSQL, runs the ETL once, writes raw/reject artifacts to the mounted `data/` directory, and exits. PostgreSQL is exposed on host port `5435`.

Run the ETL again with:

```bash
docker compose run --rm etl
```

The source data is synthetic sample order data plus public demonstration customer records. No real customer or payment information is included.

## Run locally without Docker

Requirements: Python 3.11+ and PostgreSQL 16+.

```bash
python -m venv .venv
# Windows PowerShell: .venv\\Scripts\\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
```

Create a PostgreSQL database, set `DATABASE_URL` in `.env`, and run from the repository root:

```bash
python -m etl
```

The customer source defaults to `https://jsonplaceholder.typicode.com/users` and requires internet access. Orders come from `data/source/orders.csv`. The pipeline creates the warehouse schema when it starts.

## Configuration

See `.env.example`.

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | local Compose PostgreSQL | Warehouse connection |
| `CUSTOMERS_API_URL` | JSONPlaceholder users endpoint | REST source |
| `ORDERS_CSV_PATH` | `data/source/orders.csv` | Order source |
| `RAW_DATA_DIR` | `data/raw` | Local raw landing |
| `REJECTS_DIR` | `data/rejects` | Invalid-row output |
| `AWS_S3_BUCKET` | empty | Optional S3 archive bucket |
| `AWS_REGION` | `us-east-1` | AWS region |
| `ETL_HTTP_TIMEOUT_SECONDS` | `20` | Source API timeout |

AWS credentials are resolved through boto3's standard provider chain (environment, shared profile, or workload role). No AWS resources are created automatically.

## Warehouse model

- `dim_customer`: one row per source customer, with normalized name, email, and company.
- `dim_date`: one row per order date, with calendar year, quarter, month, and day.
- `fact_order`: one row per source order, linked to customer and date dimensions, with amount and status.
- `etl_runs`: audit record for every pipeline execution.

The included CSV is synthetic sample data for demonstration. Reprocessing the same source order IDs updates facts rather than duplicating them.

## Data quality rules

- Customer source IDs and names are required.
- Order IDs must be unique within a file and positive.
- Each order must reference a customer returned by the customer API.
- Amounts must be numeric, finite, and non-negative.
- Status must be one of `pending`, `processing`, `shipped`, or `cancelled`.
- Invalid records are excluded from the warehouse load and written to JSON with validation reasons.

## Analytics examples

Run the queries in `sql/analytics.sql` to inspect monthly revenue, order value by customer, and ETL run health.

## Tests

```bash
pytest -q
```

The unit tests exercise customer/order normalization, date derivation, duplicate detection, invalid statuses, invalid dates and amounts, and unknown customer references. A PostgreSQL integration test verifies that the warehouse loader updates existing source order IDs without creating duplicates. GitHub Actions runs both sets of tests against a temporary PostgreSQL 16 service and compiles the Python modules; AWS credentials are not required.

## Current scope and production considerations

This is a portfolio/learning batch pipeline, not a managed enterprise platform. It does not include a scheduler, streaming ingestion, distributed compute, secrets manager, production IAM policies, PII governance, or a deployed cloud warehouse. AWS S3 archival is optional and requires a bucket and credentials configured by the operator. Add production security and operational controls before real workloads.

## Repository layout

```text
etl/
  config.py          # Environment configuration
  extract.py         # REST and CSV extraction
  transform.py       # Normalization and validation
  load.py            # PostgreSQL warehouse upserts
  storage.py         # Local raw landing and optional S3 archive
  pipeline.py        # ETL orchestration and run audit
  __main__.py         # CLI entry point
sql/
  schema.sql         # Warehouse schema
  analytics.sql      # Example analytical queries
data/
  source/            # Synthetic input CSV
  raw/               # Runtime raw extracts
  rejects/           # Runtime rejected records
tests/               # Unit tests
```
