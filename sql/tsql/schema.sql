/* =============================================================================
   schema.sql (SQL Server 2022 / T-SQL port)  |  Olist Revenue & Operations Analytics
   STATUS: hand-ported from sql/schema.sql. Parse-checked only; NOT executed against
           a SQL Server instance (none was available during development).
   Run in SSMS or Azure Data Studio, or: sqlcmd -S <server> -d <db> -i sql/tsql/schema.sql
   ============================================================================= */

IF OBJECT_ID('dw.v_order_summary', 'V') IS NOT NULL DROP VIEW dw.v_order_summary;
IF OBJECT_ID('dw.v_order_review', 'V')  IS NOT NULL DROP VIEW dw.v_order_review;
DROP TABLE IF EXISTS dw.reviews, dw.payments, dw.order_items, dw.orders, dw.products,
                     dw.sellers, dw.customers, dw.geo_zip, dw.categories;
DROP TABLE IF EXISTS stg.customers, stg.sellers, stg.products, stg.category_translation, stg.orders,
                     stg.order_items, stg.payments, stg.reviews, stg.geolocation;
GO
IF SCHEMA_ID('stg') IS NULL EXEC('CREATE SCHEMA stg');
IF SCHEMA_ID('dw')  IS NULL EXEC('CREATE SCHEMA dw');
GO

-- Staging (all text; NVARCHAR to keep Portuguese characters intact)
CREATE TABLE stg.customers (customer_id NVARCHAR(50), customer_unique_id NVARCHAR(50), customer_zip_code_prefix NVARCHAR(10),
                            customer_city NVARCHAR(100), customer_state NVARCHAR(5));
CREATE TABLE stg.sellers (seller_id NVARCHAR(50), seller_zip_code_prefix NVARCHAR(10), seller_city NVARCHAR(100), seller_state NVARCHAR(5));
CREATE TABLE stg.products (product_id NVARCHAR(50), product_category_name NVARCHAR(100), product_name_lenght NVARCHAR(20),
                           product_description_lenght NVARCHAR(20), product_photos_qty NVARCHAR(20), product_weight_g NVARCHAR(20),
                           product_length_cm NVARCHAR(20), product_height_cm NVARCHAR(20), product_width_cm NVARCHAR(20));
CREATE TABLE stg.category_translation (product_category_name NVARCHAR(100), product_category_name_english NVARCHAR(100));
CREATE TABLE stg.orders (order_id NVARCHAR(50), customer_id NVARCHAR(50), order_status NVARCHAR(20), order_purchase_timestamp NVARCHAR(30),
                         order_approved_at NVARCHAR(30), order_delivered_carrier_date NVARCHAR(30),
                         order_delivered_customer_date NVARCHAR(30), order_estimated_delivery_date NVARCHAR(30));
CREATE TABLE stg.order_items (order_id NVARCHAR(50), order_item_id NVARCHAR(10), product_id NVARCHAR(50), seller_id NVARCHAR(50),
                              shipping_limit_date NVARCHAR(30), price NVARCHAR(20), freight_value NVARCHAR(20));
CREATE TABLE stg.payments (order_id NVARCHAR(50), payment_sequential NVARCHAR(10), payment_type NVARCHAR(20),
                           payment_installments NVARCHAR(10), payment_value NVARCHAR(20));
CREATE TABLE stg.reviews (review_id NVARCHAR(50), order_id NVARCHAR(50), review_score NVARCHAR(5), review_comment_title NVARCHAR(MAX),
                          review_comment_message NVARCHAR(MAX), review_creation_date NVARCHAR(30), review_answer_timestamp NVARCHAR(30));
CREATE TABLE stg.geolocation (geolocation_zip_code_prefix NVARCHAR(10), geolocation_lat NVARCHAR(30), geolocation_lng NVARCHAR(30),
                              geolocation_city NVARCHAR(100), geolocation_state NVARCHAR(5));
GO

-- Modeled layer
CREATE TABLE dw.categories (
    category_pt VARCHAR(80) NOT NULL PRIMARY KEY,
    category_en VARCHAR(80) NOT NULL,
    is_translated_in_source BIT NOT NULL);

CREATE TABLE dw.geo_zip (
    zip_prefix CHAR(5) NOT NULL PRIMARY KEY,
    latitude FLOAT NOT NULL, longitude FLOAT NOT NULL, n_points INT NOT NULL);

CREATE TABLE dw.customers (
    customer_id CHAR(32) NOT NULL PRIMARY KEY,
    customer_unique_id CHAR(32) NOT NULL,
    zip_prefix CHAR(5) NOT NULL, city VARCHAR(80) NOT NULL, state CHAR(2) NOT NULL);
CREATE INDEX ix_customers_unique ON dw.customers(customer_unique_id);

CREATE TABLE dw.sellers (
    seller_id CHAR(32) NOT NULL PRIMARY KEY,
    zip_prefix CHAR(5) NOT NULL, city VARCHAR(80) NOT NULL, state CHAR(2) NOT NULL);

CREATE TABLE dw.products (
    product_id CHAR(32) NOT NULL PRIMARY KEY,
    category_pt VARCHAR(80) NOT NULL REFERENCES dw.categories(category_pt),
    name_length INT, description_length INT, photos_qty INT,
    weight_g INT, length_cm INT, height_cm INT, width_cm INT);

CREATE TABLE dw.orders (
    order_id CHAR(32) NOT NULL PRIMARY KEY,
    customer_id CHAR(32) NOT NULL REFERENCES dw.customers(customer_id),
    order_status VARCHAR(12) NOT NULL
        CHECK (order_status IN ('created','approved','invoiced','processing','shipped','delivered','canceled','unavailable')),
    purchase_ts DATETIME2(0) NOT NULL,
    approved_ts DATETIME2(0) NULL,
    delivered_carrier_ts DATETIME2(0) NULL,
    delivered_customer_ts DATETIME2(0) NULL,
    estimated_delivery_date DATE NOT NULL,
    dq_carrier_before_approval BIT NOT NULL,
    dq_delivered_before_carrier BIT NOT NULL,
    dq_status_date_conflict BIT NOT NULL);

CREATE TABLE dw.order_items (
    order_id CHAR(32) NOT NULL REFERENCES dw.orders(order_id),
    order_item_id INT NOT NULL,
    product_id CHAR(32) NOT NULL REFERENCES dw.products(product_id),
    seller_id CHAR(32) NOT NULL REFERENCES dw.sellers(seller_id),
    shipping_limit_ts DATETIME2(0) NOT NULL,
    price DECIMAL(10,2) NOT NULL CHECK (price > 0),
    freight_value DECIMAL(10,2) NOT NULL CHECK (freight_value >= 0),
    CONSTRAINT pk_order_items PRIMARY KEY (order_id, order_item_id));

CREATE TABLE dw.payments (
    order_id CHAR(32) NOT NULL REFERENCES dw.orders(order_id),
    payment_sequential INT NOT NULL,
    payment_type VARCHAR(12) NOT NULL,
    installments INT NOT NULL,
    payment_value DECIMAL(10,2) NOT NULL CHECK (payment_value >= 0),
    CONSTRAINT pk_payments PRIMARY KEY (order_id, payment_sequential));

CREATE TABLE dw.reviews (
    review_id CHAR(32) NOT NULL,
    order_id CHAR(32) NOT NULL REFERENCES dw.orders(order_id),
    review_score INT NOT NULL CHECK (review_score BETWEEN 1 AND 5),
    has_title BIT NOT NULL, has_message BIT NOT NULL,
    creation_date DATE NOT NULL, answer_ts DATETIME2(0) NOT NULL,
    CONSTRAINT pk_reviews PRIMARY KEY (review_id, order_id));
GO
