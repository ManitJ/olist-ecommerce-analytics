-- =============================================================================
-- validation.sql  |  Data-quality and reconciliation checks
-- Every check returns: check_name, expected, actual, status (PASS / FAIL / INFO)
-- python -m olist_ba.run_sql fails the build if any status = 'FAIL'.
-- =============================================================================

-- @query v01_row_counts_stg_vs_dw
-- @question Did every raw row land in the modeled layer (no silent drops)?
SELECT t.check_name, t.expected, t.actual,
       CASE WHEN t.expected = t.actual THEN 'PASS' ELSE 'FAIL' END AS status
FROM (
    SELECT 'customers'   AS check_name, (SELECT COUNT(*) FROM stg.customers)   AS expected, (SELECT COUNT(*) FROM dw.customers)   AS actual UNION ALL
    SELECT 'sellers',     (SELECT COUNT(*) FROM stg.sellers),     (SELECT COUNT(*) FROM dw.sellers)     UNION ALL
    SELECT 'products',    (SELECT COUNT(*) FROM stg.products),    (SELECT COUNT(*) FROM dw.products)    UNION ALL
    SELECT 'orders',      (SELECT COUNT(*) FROM stg.orders),      (SELECT COUNT(*) FROM dw.orders)      UNION ALL
    SELECT 'order_items', (SELECT COUNT(*) FROM stg.order_items), (SELECT COUNT(*) FROM dw.order_items) UNION ALL
    SELECT 'payments',    (SELECT COUNT(*) FROM stg.payments),    (SELECT COUNT(*) FROM dw.payments)    UNION ALL
    SELECT 'reviews',     (SELECT COUNT(*) FROM stg.reviews),     (SELECT COUNT(*) FROM dw.reviews)
) t;

-- @query v02_primary_key_uniqueness
-- @question Are business keys unique at the documented grain?
SELECT check_name, 0 AS expected, dupes AS actual,
       CASE WHEN dupes = 0 THEN 'PASS' ELSE 'FAIL' END AS status
FROM (
    SELECT 'orders.order_id' AS check_name, COUNT(*) - COUNT(DISTINCT order_id) AS dupes FROM dw.orders UNION ALL
    SELECT 'customers.customer_id', COUNT(*) - COUNT(DISTINCT customer_id) FROM dw.customers UNION ALL
    SELECT 'products.product_id',   COUNT(*) - COUNT(DISTINCT product_id)  FROM dw.products  UNION ALL
    SELECT 'order_items(order_id,order_item_id)',
           COUNT(*) - (SELECT COUNT(*) FROM (SELECT DISTINCT order_id, order_item_id FROM dw.order_items) d) FROM dw.order_items UNION ALL
    SELECT 'v_order_summary.order_id', COUNT(*) - COUNT(DISTINCT order_id) FROM dw.v_order_summary
) t;

-- @query v03_referential_integrity
-- @question Does every child row have a parent (no orphans)?
SELECT check_name, 0 AS expected, orphans AS actual,
       CASE WHEN orphans = 0 THEN 'PASS' ELSE 'FAIL' END AS status
FROM (
    SELECT 'order_items -> orders' AS check_name, COUNT(*) AS orphans
      FROM dw.order_items i LEFT JOIN dw.orders o ON o.order_id = i.order_id WHERE o.order_id IS NULL UNION ALL
    SELECT 'order_items -> products', COUNT(*)
      FROM dw.order_items i LEFT JOIN dw.products p ON p.product_id = i.product_id WHERE p.product_id IS NULL UNION ALL
    SELECT 'order_items -> sellers', COUNT(*)
      FROM dw.order_items i LEFT JOIN dw.sellers s ON s.seller_id = i.seller_id WHERE s.seller_id IS NULL UNION ALL
    SELECT 'orders -> customers', COUNT(*)
      FROM dw.orders o LEFT JOIN dw.customers c ON c.customer_id = o.customer_id WHERE c.customer_id IS NULL UNION ALL
    SELECT 'payments -> orders', COUNT(*)
      FROM dw.payments p LEFT JOIN dw.orders o ON o.order_id = p.order_id WHERE o.order_id IS NULL UNION ALL
    SELECT 'reviews -> orders', COUNT(*)
      FROM dw.reviews r LEFT JOIN dw.orders o ON o.order_id = r.order_id WHERE o.order_id IS NULL UNION ALL
    SELECT 'products -> categories', COUNT(*)
      FROM dw.products p LEFT JOIN dw.categories c ON c.category_pt = p.category_pt WHERE c.category_pt IS NULL
) t;

-- @query v04_financial_reconciliation
-- @question Do typed revenue totals equal raw text totals to the cent?
SELECT check_name, expected, actual,
       CASE WHEN ABS(expected - actual) < 0.005 THEN 'PASS' ELSE 'FAIL' END AS status
FROM (
    SELECT 'sum(price) stg vs dw' AS check_name,
           (SELECT SUM(CAST(price AS DECIMAL(14,2))) FROM stg.order_items) AS expected,
           (SELECT SUM(price) FROM dw.order_items) AS actual UNION ALL
    SELECT 'sum(freight) stg vs dw',
           (SELECT SUM(CAST(freight_value AS DECIMAL(14,2))) FROM stg.order_items),
           (SELECT SUM(freight_value) FROM dw.order_items) UNION ALL
    SELECT 'sum(payment_value) stg vs dw',
           (SELECT SUM(CAST(payment_value AS DECIMAL(14,2))) FROM stg.payments),
           (SELECT SUM(payment_value) FROM dw.payments) UNION ALL
    SELECT 'v_order_summary.product_revenue vs order_items',
           (SELECT SUM(price) FROM dw.order_items),
           (SELECT SUM(product_revenue) FROM dw.v_order_summary)
) t;

-- @query v05_payment_vs_items
-- @question How closely do customer payments match item price + freight per order?
-- Differences are expected (e.g., installment interest, vouchers); threshold: >= 99% of orders within R$0.01.
WITH j AS (
    SELECT order_id, payment_total, gmv, ABS(payment_total - gmv) AS diff
    FROM dw.v_order_summary
    WHERE payment_total IS NOT NULL AND item_count > 0
)
SELECT 'share of orders with |payment - (price+freight)| <= 0.01' AS check_name,
       0.99 AS expected,
       ROUND(AVG(CASE WHEN diff <= 0.01 THEN 1.0 ELSE 0.0 END), 4) AS actual,
       CASE WHEN AVG(CASE WHEN diff <= 0.01 THEN 1.0 ELSE 0.0 END) >= 0.99 THEN 'PASS' ELSE 'FAIL' END AS status
FROM j
UNION ALL
SELECT 'orders with payment > items by more than R$1', NULL,
       SUM(CASE WHEN payment_total - gmv > 1 THEN 1 ELSE 0 END), 'INFO' FROM j
UNION ALL
SELECT 'orders with payment < items by more than R$1', NULL,
       SUM(CASE WHEN gmv - payment_total > 1 THEN 1 ELSE 0 END), 'INFO' FROM j;

-- @query v06_business_rules
-- @question Do cleaned values respect business rules?
SELECT check_name, 0 AS expected, violations AS actual,
       CASE WHEN violations = 0 THEN 'PASS' ELSE 'FAIL' END AS status
FROM (
    SELECT 'delivered orders with zero items' AS check_name,
           COUNT(*) AS violations FROM dw.v_order_summary WHERE order_status = 'delivered' AND item_count = 0 UNION ALL
    SELECT 'delivery before purchase', COUNT(*) FROM dw.v_order_summary WHERE delivery_days < 0 UNION ALL
    SELECT 'approval before purchase', COUNT(*) FROM dw.v_order_summary WHERE approval_hours < 0 UNION ALL
    SELECT 'review score outside 1-5', COUNT(*) FROM dw.reviews WHERE review_score NOT BETWEEN 1 AND 5 UNION ALL
    SELECT 'non-positive item price', COUNT(*) FROM dw.order_items WHERE price <= 0 UNION ALL
    SELECT 'zip prefix not 5 chars', COUNT(*) FROM dw.customers WHERE LENGTH(zip_prefix) <> 5
) t;

-- @query v07_analysis_window
-- @question Does the analysis window contain exactly 20 complete months, and what is excluded?
SELECT 'months in window' AS check_name, 20 AS expected,
       COUNT(DISTINCT purchase_month) AS actual,
       CASE WHEN COUNT(DISTINCT purchase_month) = 20 THEN 'PASS' ELSE 'FAIL' END AS status
FROM dw.v_order_summary WHERE in_window = 1
UNION ALL
SELECT 'orders outside window (excluded from trend KPIs)', NULL, COUNT(*), 'INFO'
FROM dw.v_order_summary WHERE in_window = 0;

-- @query v08_data_quality_flags
-- @question How many rows carry data-quality flags (kept, but visible)?
SELECT 'carrier handoff before payment approval' AS check_name, NULL AS expected,
       SUM(CASE WHEN dq_carrier_before_approval = TRUE THEN 1 ELSE 0 END) AS actual, 'INFO' AS status FROM dw.orders
UNION ALL
SELECT 'customer delivery before carrier handoff', NULL,
       SUM(CASE WHEN dq_delivered_before_carrier = TRUE THEN 1 ELSE 0 END), 'INFO' FROM dw.orders
UNION ALL
SELECT 'status/date conflict', NULL,
       SUM(CASE WHEN dq_status_date_conflict = TRUE THEN 1 ELSE 0 END), 'INFO' FROM dw.orders
UNION ALL
SELECT 'products with unknown category', NULL,
       SUM(CASE WHEN category_pt = 'unknown' THEN 1 ELSE 0 END), 'INFO' FROM dw.products
UNION ALL
SELECT 'orders with more than one review (latest kept in views)', NULL,
       COUNT(*), 'INFO' FROM (SELECT order_id FROM dw.reviews GROUP BY order_id HAVING COUNT(*) > 1) d
UNION ALL
SELECT 'orders with no payment record', NULL,
       COUNT(*), 'INFO' FROM dw.v_order_summary WHERE payment_total IS NULL;
