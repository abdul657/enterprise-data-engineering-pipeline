# Enterprise Data Engineering Pipeline

A reproducible Python ETL project that ingests customer records from a REST API and order records from CSV, validates and transforms the data, lands raw extracts, and loads analytics-ready tables into PostgreSQL.

## What it demonstrates

- **Extract:** Retrieve customer records from JSONPlaceholder and read source orders from CSV.
- **Raw data lake:** Persist unmodified API responses and source CSV snapshots locally under `data/raw/`.
- **Transform:** Normalize customer and order fields, parse timestamps and monetary values, and derive date attributes.
- **Data quality:** Validate required fields, customer references, order statuses, amount bounds, and duplicate source IDs. Invalid rows are written to a rejects file with reasons.
- **Warehouse:** Load a small star schema with `dim_customer`, `dim_date`, and `fact_order`; use PostgreSQL upserts so repeat runs are idempotent.
- **Run observability:** Record run status, start/end times, and extracted/loaded/rejected row counts in `etl_runs`.
- **Cloud option:** Optionally upload raw extracts and reject files to an S3 bucket using the standard AWS credential chain.
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

The pipeline container waits for PostgreSQL, runs the ETL once, writes local raw/reject artifacts to the mounted `data/` directory, and exits. The database is exposed on host port `5435`.

To run the ETL again:

```bash
docker compose run --rm etl
```

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

Create a local PostgreSQL database, set `DATABASE_URL` in `.env`, then run:

```bash
python -m etl
```

The default customer source is `https://jsonplaceholder.typicode.com/users`. The pipeline requires network access to fetch it. Order rows come from `data/source/orders.csv`.

## Configuration

See `.env.example`.

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | local Compose PostgreSQL | Warehouse connection |
| `CUSTOMERS_API_URL` | JSONPlaceholder users endpoint | REST source |
| `ORDERS_CSV_PATH` | `data/source/orders.csv` | Order source file |
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
- `etl_runs`: operational audit record for every pipeline execution.

The included CSV is synthetic sample data for demonstration, not real customer or payment information. Reprocessing the same source order IDs updates records rather than duplicating them.

## Data quality rules

- Customer source IDs and names are required.
- Order IDs must be unique within a file and positive.
- Each order must reference a customer returned by the customer API.
- Amounts must be numeric and non-negative.
- Status must be one of `pending`, `processing`, `shipped`, or `cancelled`.
- Invalid records are excluded from the warehouse load and written to JSON with validation reasons.

## Tests

```bash
pytest -q
```

Unit tests use fixture data and SQLite-compatible test logic for transformations and validation; the production loader targets PostgreSQL. The GitHub Actions workflow runs the unit tests and Python compile checks without requiring AWS credentials or a live external database.

## Current scope and production considerations

This is a portfolio/learning pipeline, not a managed enterprise platform. It demonstrates a batch ETL pattern and a dimensional warehouse model. It does not include a scheduler, streaming ingestion, distributed compute, secrets manager, production IAM policies, PII governance, or a deployed cloud warehouse. Add those controls and operational services before production use.

## Repository layout

```text
etl/
  config.py          # Typed environment configuration
  extract.py         # REST and CSV extraction
  transform.py       # Normalization and validation
  load.py            # PostgreSQL warehouse upserts
  storage.py         # Local raw landing and optional S3 archive
  pipeline.py        # ETL orchestration and run audit
  __main__.py        # CLI entry point
sql/
  schema.sql         # Warehouse schema
data/
  source/            # Synthetic input CSV
  raw/               # Runtime raw extracts
  rejects/           # Runtime rejected records
tests/               # Unit tests
```
