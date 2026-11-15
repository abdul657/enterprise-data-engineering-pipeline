CREATE TABLE IF NOT EXISTS dim_customer (
    customer_key BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source_customer_id INTEGER NOT NULL UNIQUE,
    customer_name VARCHAR(180) NOT NULL,
    email VARCHAR(254),
    company VARCHAR(180),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS dim_date (
    date_key INTEGER PRIMARY KEY,
    calendar_date DATE NOT NULL UNIQUE,
    calendar_year SMALLINT NOT NULL,
    calendar_quarter SMALLINT NOT NULL CHECK (calendar_quarter BETWEEN 1 AND 4),
    calendar_month SMALLINT NOT NULL CHECK (calendar_month BETWEEN 1 AND 12),
    calendar_day SMALLINT NOT NULL CHECK (calendar_day BETWEEN 1 AND 31)
);

CREATE TABLE IF NOT EXISTS fact_order (
    source_order_id BIGINT PRIMARY KEY,
    customer_key BIGINT NOT NULL REFERENCES dim_customer(customer_key),
    date_key INTEGER NOT NULL REFERENCES dim_date(date_key),
    order_timestamp TIMESTAMPTZ NOT NULL,
    amount NUMERIC(14, 2) NOT NULL CHECK (amount >= 0),
    status VARCHAR(24) NOT NULL CHECK (status IN ('pending', 'processing', 'shipped', 'cancelled')),
    source_system VARCHAR(40) NOT NULL DEFAULT 'sample_orders_csv',
    loaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_fact_order_customer ON fact_order(customer_key);
CREATE INDEX IF NOT EXISTS idx_fact_order_date ON fact_order(date_key);
CREATE INDEX IF NOT EXISTS idx_fact_order_status ON fact_order(status);

CREATE TABLE IF NOT EXISTS etl_runs (
    run_id UUID PRIMARY KEY,
    status VARCHAR(20) NOT NULL CHECK (status IN ('running', 'succeeded', 'failed')),
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    customers_extracted INTEGER NOT NULL DEFAULT 0,
    orders_extracted INTEGER NOT NULL DEFAULT 0,
    customers_loaded INTEGER NOT NULL DEFAULT 0,
    orders_loaded INTEGER NOT NULL DEFAULT 0,
    rejected_records INTEGER NOT NULL DEFAULT 0,
    error_message TEXT
);
