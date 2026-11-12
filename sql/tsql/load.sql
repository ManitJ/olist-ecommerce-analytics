/* =============================================================================
   load.sql (SQL Server 2022 / T-SQL port)
   STATUS: hand-ported from sql/load.sql. Parse-checked only; NOT executed against
           SQL Server. Run in SQLCMD mode (SSMS: Query > SQLCMD Mode) or with sqlcmd:
     sqlcmd -S <server> -d <db> -v RawDir="C:\path\to\data\raw" -i sql/tsql/load.sql
   The CSV files must be readable by the SQL Server service account.
   ============================================================================= */
:setvar RawDir "C:\olist\data\raw"

-- 1. Staging ------------------------------------------------------------------
BULK INSERT stg.customers   FROM '$(RawDir)\olist_customers_dataset.csv'      WITH (FORMAT = 'CSV', FIRSTROW = 2, FIELDQUOTE = '"', CODEPAGE = '65001', ROWTERMINATOR = '0x0a');
BULK INSERT stg.sellers     FROM '$(RawDir)\olist_sellers_dataset.csv'        WITH (FORMAT = 'CSV', FIRSTROW = 2, FIELDQUOTE = '"', CODEPAGE = '65001', ROWTERMINATOR = '0x0a');
BULK INSERT stg.products    FROM '$(RawDir)\olist_products_dataset.csv'       WITH (FORMAT = 'CSV', FIRSTROW = 2, FIELDQUOTE = '"', CODEPAGE = '65001', ROWTERMINATOR = '0x0a');
BULK INSERT stg.category_translation FROM '$(RawDir)\product_category_name_translation.csv' WITH (FORMAT = 'CSV', FIRSTROW = 2, FIELDQUOTE = '"', CODEPAGE = '65001', ROWTERMINATOR = '0x0a');
BULK INSERT stg.orders      FROM '$(RawDir)\olist_orders_dataset.csv'         WITH (FORMAT = 'CSV', FIRSTROW = 2, FIELDQUOTE = '"', CODEPAGE = '65001', ROWTERMINATOR = '0x0a');
BULK INSERT stg.order_items FROM '$(RawDir)\olist_order_items_dataset.csv'    WITH (FORMAT = 'CSV', FIRSTROW = 2, FIELDQUOTE = '"', CODEPAGE = '65001', ROWTERMINATOR = '0x0a');
BULK INSERT stg.payments    FROM '$(RawDir)\olist_order_payments_dataset.csv' WITH (FORMAT = 'CSV', FIRSTROW = 2, FIELDQUOTE = '"', CODEPAGE = '65001', ROWTERMINATOR = '0x0a');
BULK INSERT stg.reviews     FROM '$(RawDir)\olist_order_reviews_dataset.csv'  WITH (FORMAT = 'CSV', FIRSTROW = 2, FIELDQUOTE = '"', CODEPAGE = '65001', ROWTERMINATOR = '0x0a');
BULK INSERT stg.geolocation FROM '$(RawDir)\olist_geolocation_dataset.csv'    WITH (FORMAT = 'CSV', FIRSTROW = 2, FIELDQUOTE = '"', CODEPAGE = '65001', ROWTERMINATOR = '0x0a');
GO

-- Empty strings from BULK INSERT become NULL-equivalent via NULLIF below.

-- 2. Categories ---------------------------------------------------------------
INSERT INTO dw.categories (category_pt, category_en, is_translated_in_source)
SELECT TRIM(product_category_name), TRIM(product_category_name_english), 1 FROM stg.category_translation;

INSERT INTO dw.categories (category_pt, category_en, is_translated_in_source)
SELECT v.category_pt, v.category_en, 0
FROM (VALUES ('pc_gamer', 'pc_gamer'),
             ('portateis_cozinha_e_preparadores_de_alimentos', 'portable_kitchen_food_preparers'),
             ('unknown', 'unknown')) AS v(category_pt, category_en)
WHERE v.category_pt NOT IN (SELECT category_pt FROM dw.categories);

-- 3. Geolocation centroid per zip prefix (Brazil bounding box only) -------------
INSERT INTO dw.geo_zip (zip_prefix, latitude, longitude, n_points)
SELECT RIGHT('00000' + geolocation_zip_code_prefix, 5), AVG(lat), AVG(lng), COUNT(*)
FROM (SELECT geolocation_zip_code_prefix,
             TRY_CAST(geolocation_lat AS FLOAT) AS lat, TRY_CAST(geolocation_lng AS FLOAT) AS lng
      FROM stg.geolocation) g
WHERE lat BETWEEN -33.75 AND 5.27 AND lng BETWEEN -73.99 AND -34.79
GROUP BY RIGHT('00000' + geolocation_zip_code_prefix, 5);

-- 4. Customers & sellers (accent folding via code-page conversion) -------------
INSERT INTO dw.customers (customer_id, customer_unique_id, zip_prefix, city, state)
SELECT customer_id, customer_unique_id,
       RIGHT('00000' + customer_zip_code_prefix, 5),
       LOWER(TRIM(CAST(customer_city COLLATE SQL_Latin1_General_CP1253_CI_AI AS VARCHAR(80)))),
       UPPER(TRIM(customer_state))
FROM stg.customers;

INSERT INTO dw.sellers (seller_id, zip_prefix, city, state)
SELECT seller_id,
       RIGHT('00000' + seller_zip_code_prefix, 5),
       LOWER(TRIM(CAST(seller_city COLLATE SQL_Latin1_General_CP1253_CI_AI AS VARCHAR(80)))),
       UPPER(TRIM(seller_state))
FROM stg.sellers;

-- 5. Products -----------------------------------------------------------------
INSERT INTO dw.products
SELECT product_id,
       COALESCE(NULLIF(TRIM(product_category_name), ''), 'unknown'),
       TRY_CAST(TRY_CAST(NULLIF(product_name_lenght, '')        AS FLOAT) AS INT),
       TRY_CAST(TRY_CAST(NULLIF(product_description_lenght, '') AS FLOAT) AS INT),
       TRY_CAST(TRY_CAST(NULLIF(product_photos_qty, '')         AS FLOAT) AS INT),
       TRY_CAST(TRY_CAST(NULLIF(product_weight_g, '')           AS FLOAT) AS INT),
       TRY_CAST(TRY_CAST(NULLIF(product_length_cm, '')          AS FLOAT) AS INT),
       TRY_CAST(TRY_CAST(NULLIF(product_height_cm, '')          AS FLOAT) AS INT),
       TRY_CAST(TRY_CAST(NULLIF(product_width_cm, '')           AS FLOAT) AS INT)
FROM stg.products;

-- 6. Orders with data-quality flags ---------------------------------------------
WITH typed AS (
    SELECT order_id, customer_id, LOWER(TRIM(order_status)) AS order_status,
           TRY_CAST(NULLIF(order_purchase_timestamp, '')      AS DATETIME2(0)) AS purchase_ts,
           TRY_CAST(NULLIF(order_approved_at, '')             AS DATETIME2(0)) AS approved_ts,
           TRY_CAST(NULLIF(order_delivered_carrier_date, '')  AS DATETIME2(0)) AS delivered_carrier_ts,
           TRY_CAST(NULLIF(order_delivered_customer_date, '') AS DATETIME2(0)) AS delivered_customer_ts,
           CAST(TRY_CAST(order_estimated_delivery_date AS DATETIME2(0)) AS DATE) AS estimated_delivery_date
    FROM stg.orders
)
INSERT INTO dw.orders
SELECT *,
       CASE WHEN delivered_carrier_ts < approved_ts THEN 1 ELSE 0 END,
       CASE WHEN delivered_customer_ts < delivered_carrier_ts THEN 1 ELSE 0 END,
       CASE WHEN (order_status = 'delivered' AND delivered_customer_ts IS NULL)
              OR (order_status = 'canceled' AND delivered_customer_ts IS NOT NULL) THEN 1 ELSE 0 END
FROM typed;

-- 7. Items, payments, reviews ---------------------------------------------------
INSERT INTO dw.order_items
SELECT order_id, CAST(order_item_id AS INT), product_id, seller_id,
       CAST(shipping_limit_date AS DATETIME2(0)),
       CAST(price AS DECIMAL(10,2)), CAST(freight_value AS DECIMAL(10,2))
FROM stg.order_items;

INSERT INTO dw.payments
SELECT order_id, CAST(payment_sequential AS INT), LOWER(TRIM(payment_type)),
       CAST(payment_installments AS INT), CAST(payment_value AS DECIMAL(10,2))
FROM stg.payments;

INSERT INTO dw.reviews
SELECT review_id, order_id, CAST(review_score AS INT),
       CASE WHEN NULLIF(TRIM(review_comment_title), '')   IS NOT NULL THEN 1 ELSE 0 END,
       CASE WHEN NULLIF(TRIM(review_comment_message), '') IS NOT NULL THEN 1 ELSE 0 END,
       CAST(CAST(review_creation_date AS DATETIME2(0)) AS DATE),
       CAST(review_answer_timestamp AS DATETIME2(0))
FROM stg.reviews;
GO

-- 8. Views ----------------------------------------------------------------------
CREATE VIEW dw.v_order_review AS
SELECT order_id, review_score, has_message
FROM (SELECT r.*, ROW_NUMBER() OVER (PARTITION BY order_id ORDER BY answer_ts DESC, review_id) AS rn
      FROM dw.reviews r) x
WHERE rn = 1;
GO

CREATE VIEW dw.v_order_summary AS
WITH items AS (
    SELECT order_id, COUNT(*) AS item_count, COUNT(DISTINCT seller_id) AS seller_count,
           SUM(price) AS product_revenue, SUM(freight_value) AS freight_revenue,
           MAX(shipping_limit_ts) AS shipping_limit_ts
    FROM dw.order_items GROUP BY order_id
), pay AS (
    SELECT order_id, SUM(payment_value) AS payment_total, MAX(installments) AS max_installments
    FROM dw.payments GROUP BY order_id
)
SELECT o.order_id, o.customer_id, c.customer_unique_id, c.state AS customer_state, o.order_status,
       o.purchase_ts,
       CAST(o.purchase_ts AS DATE)                                   AS purchase_date,
       CAST(DATETRUNC(month, o.purchase_ts) AS DATE)                 AS purchase_month,
       CASE WHEN o.purchase_ts >= '2017-01-01' AND o.purchase_ts < '2018-09-01' THEN 1 ELSE 0 END AS in_window,
       CASE WHEN o.order_status NOT IN ('canceled', 'unavailable') THEN 1 ELSE 0 END             AS is_revenue_order,
       CASE WHEN o.order_status = 'delivered' AND o.delivered_customer_ts IS NOT NULL THEN 1 ELSE 0 END AS is_delivered,
       COALESCE(i.item_count, 0)      AS item_count,
       COALESCE(i.seller_count, 0)    AS seller_count,
       COALESCE(i.product_revenue, 0) AS product_revenue,
       COALESCE(i.freight_revenue, 0) AS freight_revenue,
       COALESCE(i.product_revenue, 0) + COALESCE(i.freight_revenue, 0) AS gmv,
       p.payment_total, p.max_installments,
       DATEDIFF(SECOND, o.purchase_ts, o.approved_ts) / 3600.0                AS approval_hours,
       DATEDIFF(SECOND, o.approved_ts, o.delivered_carrier_ts) / 86400.0      AS seller_to_carrier_days,
       DATEDIFF(SECOND, o.delivered_carrier_ts, o.delivered_customer_ts) / 86400.0 AS carrier_to_customer_days,
       DATEDIFF(SECOND, o.purchase_ts, o.delivered_customer_ts) / 86400.0     AS delivery_days,
       DATEDIFF(DAY, o.estimated_delivery_date, CAST(o.delivered_customer_ts AS DATE)) AS days_vs_estimate,
       CASE WHEN o.delivered_customer_ts IS NULL THEN NULL
            WHEN CAST(o.delivered_customer_ts AS DATE) > o.estimated_delivery_date THEN 1 ELSE 0 END AS is_late,
       CASE WHEN o.delivered_carrier_ts IS NULL OR i.shipping_limit_ts IS NULL THEN NULL
            WHEN o.delivered_carrier_ts > i.shipping_limit_ts THEN 1 ELSE 0 END AS seller_shipped_late,
       DATEDIFF(DAY, CAST(o.purchase_ts AS DATE), o.estimated_delivery_date) AS promised_days,
       r.review_score,
       o.dq_carrier_before_approval, o.dq_delivered_before_carrier, o.dq_status_date_conflict
FROM dw.orders o
JOIN dw.customers c ON c.customer_id = o.customer_id
LEFT JOIN items i ON i.order_id = o.order_id
LEFT JOIN pay p ON p.order_id = o.order_id
LEFT JOIN dw.v_order_review r ON r.order_id = o.order_id;
GO
