-- Monthly revenue and order volume
SELECT
    dd.calendar_year,
    dd.calendar_month,
    COUNT(*) AS order_count,
    SUM(fo.amount) AS gross_order_value
FROM fact_order AS fo
JOIN dim_date AS dd ON dd.date_key = fo.date_key
WHERE fo.status <> 'cancelled'
GROUP BY dd.calendar_year, dd.calendar_month
ORDER BY dd.calendar_year, dd.calendar_month;

-- Revenue and order volume by customer
SELECT
    dc.customer_name,
    dc.company,
    COUNT(*) AS order_count,
    SUM(fo.amount) AS lifetime_order_value
FROM fact_order AS fo
JOIN dim_customer AS dc ON dc.customer_key = fo.customer_key
WHERE fo.status <> 'cancelled'
GROUP BY dc.customer_name, dc.company
ORDER BY lifetime_order_value DESC;

-- ETL health and rejected-record trend
SELECT
    run_id,
    status,
    started_at,
    completed_at,
    customers_loaded,
    orders_loaded,
    rejected_records,
    error_message
FROM etl_runs
ORDER BY started_at DESC;
