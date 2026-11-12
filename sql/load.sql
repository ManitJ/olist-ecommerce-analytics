-- =============================================================================
-- load.sql  |  Load raw CSVs into stg.*, then clean/type/key into dw.*
-- Engine: DuckDB. Run from the repository root (paths are relative to it).
-- Every cleaning rule below is documented in docs/data_cleaning_log.md.
-- =============================================================================

SET VARIABLE raw_dir = 'data/raw';

-- ---------------------------------------------------------------------------
-- 1. Staging: raw text, no transformations
-- ---------------------------------------------------------------------------
INSERT INTO stg.customers  SELECT * FROM read_csv(getvariable('raw_dir') || '/olist_customers_dataset.csv',      header = true, all_varchar = true);
INSERT INTO stg.sellers    SELECT * FROM read_csv(getvariable('raw_dir') || '/olist_sellers_dataset.csv',        header = true, all_varchar = true);
INSERT INTO stg.products   SELECT * FROM read_csv(getvariable('raw_dir') || '/olist_products_dataset.csv',       header = true, all_varchar = true);
INSERT INTO stg.category_translation SELECT * FROM read_csv(getvariable('raw_dir') || '/product_category_name_translation.csv', header = true, all_varchar = true);
INSERT INTO stg.orders     SELECT * FROM read_csv(getvariable('raw_dir') || '/olist_orders_dataset.csv',         header = true, all_varchar = true);
INSERT INTO stg.order_items SELECT * FROM read_csv(getvariable('raw_dir') || '/olist_order_items_dataset.csv',   header = true, all_varchar = true);
INSERT INTO stg.payments   SELECT * FROM read_csv(getvariable('raw_dir') || '/olist_order_payments_dataset.csv', header = true, all_varchar = true);
INSERT INTO stg.reviews    SELECT * FROM read_csv(getvariable('raw_dir') || '/olist_order_reviews_dataset.csv',  header = true, all_varchar = true);
INSERT INTO stg.geolocation SELECT * FROM read_csv(getvariable('raw_dir') || '/olist_geolocation_dataset.csv',   header = true, all_varchar = true);

-- ---------------------------------------------------------------------------
-- 2. Categories: source translations + 2 missing translations + 'unknown'
-- ---------------------------------------------------------------------------
INSERT INTO dw.categories
SELECT TRIM(product_category_name), TRIM(product_category_name_english), TRUE
FROM stg.category_translation;

INSERT INTO dw.categories
SELECT v.category_pt, v.category_en, FALSE
FROM (VALUES
        ('pc_gamer', 'pc_gamer'),
        ('portateis_cozinha_e_preparadores_de_alimentos', 'portable_kitchen_food_preparers'),
        ('unknown', 'unknown')) AS v(category_pt, category_en)
WHERE v.category_pt NOT IN (SELECT category_pt FROM dw.categories);

-- ---------------------------------------------------------------------------
-- 3. Geolocation: drop points outside Brazil's bounding box, average per zip
-- ---------------------------------------------------------------------------
INSERT INTO dw.geo_zip
SELECT LPAD(geolocation_zip_code_prefix, 5, '0'),
       AVG(CAST(geolocation_lat AS DOUBLE)),
       AVG(CAST(geolocation_lng AS DOUBLE)),
       COUNT(*)
FROM stg.geolocation
WHERE CAST(geolocation_lat AS DOUBLE) BETWEEN -33.75 AND 5.27
  AND CAST(geolocation_lng AS DOUBLE) BETWEEN -73.99 AND -34.79
GROUP BY 1;

-- ---------------------------------------------------------------------------
-- 4. Customers & sellers: restore zero-padded zip, normalise city text
-- ---------------------------------------------------------------------------
INSERT INTO dw.customers
SELECT customer_id,
       customer_unique_id,
       LPAD(customer_zip_code_prefix, 5, '0'),
       LOWER(TRIM(strip_accents(customer_city))),
       UPPER(TRIM(customer_state))
FROM stg.customers;

INSERT INTO dw.sellers
SELECT seller_id,
       LPAD(seller_zip_code_prefix, 5, '0'),
       LOWER(TRIM(strip_accents(seller_city))),
       UPPER(TRIM(seller_state))
FROM stg.sellers;

-- ---------------------------------------------------------------------------
-- 5. Products: NULL category -> 'unknown'; fix source column-name typos
-- ---------------------------------------------------------------------------
INSERT INTO dw.products
SELECT product_id,
       COALESCE(NULLIF(TRIM(product_category_name), ''), 'unknown'),
       CAST(CAST(product_name_lenght        AS DOUBLE) AS INTEGER),
       CAST(CAST(product_description_lenght AS DOUBLE) AS INTEGER),
       CAST(CAST(product_photos_qty         AS DOUBLE) AS INTEGER),
       CAST(CAST(product_weight_g           AS DOUBLE) AS INTEGER),
       CAST(CAST(product_length_cm          AS DOUBLE) AS INTEGER),
       CAST(CAST(product_height_cm          AS DOUBLE) AS INTEGER),
       CAST(CAST(product_width_cm           AS DOUBLE) AS INTEGER)
FROM stg.products;

-- ---------------------------------------------------------------------------
-- 6. Orders: type timestamps, add data-quality flags (no rows removed)
-- ---------------------------------------------------------------------------
INSERT INTO dw.orders
WITH typed AS (
    SELECT order_id, customer_id, LOWER(TRIM(order_status)) AS order_status,
           CAST(order_purchase_timestamp      AS TIMESTAMP) AS purchase_ts,
           CAST(order_approved_at             AS TIMESTAMP) AS approved_ts,
           CAST(order_delivered_carrier_date  AS TIMESTAMP) AS delivered_carrier_ts,
           CAST(order_delivered_customer_date AS TIMESTAMP) AS delivered_customer_ts,
           CAST(CAST(order_estimated_delivery_date AS TIMESTAMP) AS DATE) AS estimated_delivery_date
    FROM stg.orders
)
SELECT *,
       COALESCE(delivered_carrier_ts < approved_ts, FALSE),
       COALESCE(delivered_customer_ts < delivered_carrier_ts, FALSE),
       (order_status = 'delivered' AND delivered_customer_ts IS NULL)
         OR (order_status = 'canceled' AND delivered_customer_ts IS NOT NULL)
FROM typed;

-- ---------------------------------------------------------------------------
-- 7. Order items & payments
-- ---------------------------------------------------------------------------
INSERT INTO dw.order_items
SELECT order_id, CAST(order_item_id AS INTEGER), product_id, seller_id,
       CAST(shipping_limit_date AS TIMESTAMP),
       CAST(price AS DECIMAL(10,2)), CAST(freight_value AS DECIMAL(10,2))
FROM stg.order_items;

INSERT INTO dw.payments
SELECT order_id, CAST(payment_sequential AS INTEGER), LOWER(TRIM(payment_type)),
       CAST(payment_installments AS INTEGER), CAST(payment_value AS DECIMAL(10,2))
FROM stg.payments;

-- ---------------------------------------------------------------------------
-- 8. Reviews: keep all (review_id, order_id) pairs; drop free text (flags only)
-- ---------------------------------------------------------------------------
INSERT INTO dw.reviews
SELECT review_id, order_id, CAST(review_score AS INTEGER),
       review_comment_title   IS NOT NULL AND TRIM(review_comment_title)   <> '',
       review_comment_message IS NOT NULL AND TRIM(review_comment_message) <> '',
       CAST(CAST(review_creation_date AS TIMESTAMP) AS DATE),
       CAST(review_answer_timestamp AS TIMESTAMP)
FROM stg.reviews;

-- =============================================================================
-- 9. Analytical views
-- =============================================================================

-- Latest review per order (551 orders have more than one review in the source)
CREATE OR REPLACE VIEW dw.v_order_review AS
SELECT order_id, review_score, has_message
FROM (
    SELECT r.*, ROW_NUMBER() OVER (PARTITION BY order_id
                                   ORDER BY answer_ts DESC, review_id) AS rn
    FROM dw.reviews r
) x
WHERE rn = 1;

-- One row per order with financial, fulfilment and experience metrics.
-- Analysis window = 2017-01-01 .. 2018-08-31 (20 complete months).
-- Flags are 0/1 integers (not BOOLEAN) for portability to SQL Server.
CREATE OR REPLACE VIEW dw.v_order_summary AS
WITH items AS (
    SELECT order_id,
           COUNT(*)                           AS item_count,
           COUNT(DISTINCT seller_id)          AS seller_count,
           SUM(price)                         AS product_revenue,
           SUM(freight_value)                 AS freight_revenue,
           MAX(shipping_limit_ts)             AS shipping_limit_ts
    FROM dw.order_items
    GROUP BY order_id
),
pay AS (
    SELECT order_id, SUM(payment_value) AS payment_total, MAX(installments) AS max_installments
    FROM dw.payments
    GROUP BY order_id
)
SELECT o.order_id,
       o.customer_id,
       c.customer_unique_id,
       c.state                                           AS customer_state,
       o.order_status,
       o.purchase_ts,
       CAST(o.purchase_ts AS DATE)                       AS purchase_date,
       CAST(DATE_TRUNC('month', o.purchase_ts) AS DATE)  AS purchase_month,
       CASE WHEN o.purchase_ts >= TIMESTAMP '2017-01-01'
             AND o.purchase_ts <  TIMESTAMP '2018-09-01' THEN 1 ELSE 0 END          AS in_window,
       CASE WHEN o.order_status NOT IN ('canceled', 'unavailable') THEN 1 ELSE 0 END AS is_revenue_order,
       CASE WHEN o.order_status = 'delivered'
             AND o.delivered_customer_ts IS NOT NULL THEN 1 ELSE 0 END              AS is_delivered,
       COALESCE(i.item_count, 0)                         AS item_count,
       COALESCE(i.seller_count, 0)                       AS seller_count,
       COALESCE(i.product_revenue, 0)                    AS product_revenue,
       COALESCE(i.freight_revenue, 0)                    AS freight_revenue,
       COALESCE(i.product_revenue, 0) + COALESCE(i.freight_revenue, 0) AS gmv,
       p.payment_total,
       p.max_installments,
       DATE_DIFF('second', o.purchase_ts, o.approved_ts) / 3600.0               AS approval_hours,
       DATE_DIFF('second', o.approved_ts, o.delivered_carrier_ts) / 86400.0     AS seller_to_carrier_days,
       DATE_DIFF('second', o.delivered_carrier_ts, o.delivered_customer_ts) / 86400.0 AS carrier_to_customer_days,
       DATE_DIFF('second', o.purchase_ts, o.delivered_customer_ts) / 86400.0    AS delivery_days,
       DATE_DIFF('day', o.estimated_delivery_date, CAST(o.delivered_customer_ts AS DATE)) AS days_vs_estimate,
       CASE WHEN o.delivered_customer_ts IS NULL THEN NULL
            WHEN CAST(o.delivered_customer_ts AS DATE) > o.estimated_delivery_date THEN 1
            ELSE 0 END                                                         AS is_late,
       CASE WHEN o.delivered_carrier_ts IS NULL OR i.shipping_limit_ts IS NULL THEN NULL
            WHEN o.delivered_carrier_ts > i.shipping_limit_ts THEN 1
            ELSE 0 END                                                         AS seller_shipped_late,
       DATE_DIFF('day', CAST(o.purchase_ts AS DATE), o.estimated_delivery_date) AS promised_days,
       r.review_score,
       o.dq_carrier_before_approval,
       o.dq_delivered_before_carrier,
       o.dq_status_date_conflict
FROM dw.orders o
JOIN dw.customers c       ON c.customer_id = o.customer_id
LEFT JOIN items i         ON i.order_id = o.order_id
LEFT JOIN pay p           ON p.order_id = o.order_id
LEFT JOIN dw.v_order_review r ON r.order_id = o.order_id;
