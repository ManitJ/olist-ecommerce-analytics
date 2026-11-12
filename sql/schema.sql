-- =============================================================================
-- schema.sql  |  Olist Revenue & Operations Analytics
-- Engine: DuckDB (development).  T-SQL port: sql/tsql/schema.sql
--
-- Two layers:
--   stg.*  raw files loaded as text, 1:1 with the source CSVs (no cleaning)
--   dw.*   cleaned, typed, keyed relational model used by all analysis
-- Run order: schema.sql -> load.sql -> validation.sql -> analysis.sql
-- =============================================================================

DROP SCHEMA IF EXISTS dw CASCADE;
DROP SCHEMA IF EXISTS stg CASCADE;
CREATE SCHEMA stg;
CREATE SCHEMA dw;

-- ---------------------------------------------------------------------------
-- Staging: everything VARCHAR so that loading never silently coerces values.
-- ---------------------------------------------------------------------------
CREATE TABLE stg.customers (
    customer_id VARCHAR, customer_unique_id VARCHAR, customer_zip_code_prefix VARCHAR,
    customer_city VARCHAR, customer_state VARCHAR);

CREATE TABLE stg.sellers (
    seller_id VARCHAR, seller_zip_code_prefix VARCHAR, seller_city VARCHAR, seller_state VARCHAR);

CREATE TABLE stg.products (
    product_id VARCHAR, product_category_name VARCHAR, product_name_lenght VARCHAR,
    product_description_lenght VARCHAR, product_photos_qty VARCHAR, product_weight_g VARCHAR,
    product_length_cm VARCHAR, product_height_cm VARCHAR, product_width_cm VARCHAR);

CREATE TABLE stg.category_translation (
    product_category_name VARCHAR, product_category_name_english VARCHAR);

CREATE TABLE stg.orders (
    order_id VARCHAR, customer_id VARCHAR, order_status VARCHAR, order_purchase_timestamp VARCHAR,
    order_approved_at VARCHAR, order_delivered_carrier_date VARCHAR,
    order_delivered_customer_date VARCHAR, order_estimated_delivery_date VARCHAR);

CREATE TABLE stg.order_items (
    order_id VARCHAR, order_item_id VARCHAR, product_id VARCHAR, seller_id VARCHAR,
    shipping_limit_date VARCHAR, price VARCHAR, freight_value VARCHAR);

CREATE TABLE stg.payments (
    order_id VARCHAR, payment_sequential VARCHAR, payment_type VARCHAR,
    payment_installments VARCHAR, payment_value VARCHAR);

CREATE TABLE stg.reviews (
    review_id VARCHAR, order_id VARCHAR, review_score VARCHAR, review_comment_title VARCHAR,
    review_comment_message VARCHAR, review_creation_date VARCHAR, review_answer_timestamp VARCHAR);

CREATE TABLE stg.geolocation (
    geolocation_zip_code_prefix VARCHAR, geolocation_lat VARCHAR, geolocation_lng VARCHAR,
    geolocation_city VARCHAR, geolocation_state VARCHAR);

-- ---------------------------------------------------------------------------
-- Modeled layer (dw). Primary and foreign keys are enforced.
-- ---------------------------------------------------------------------------
CREATE TABLE dw.categories (
    category_pt     VARCHAR(80)  NOT NULL PRIMARY KEY,
    category_en     VARCHAR(80)  NOT NULL,
    is_translated_in_source BOOLEAN NOT NULL       -- FALSE = translation added by this project
);

CREATE TABLE dw.geo_zip (
    zip_prefix  VARCHAR(5)   NOT NULL PRIMARY KEY,
    latitude    DOUBLE       NOT NULL,
    longitude   DOUBLE       NOT NULL,
    n_points    INTEGER      NOT NULL               -- raw points averaged into this centroid
);

CREATE TABLE dw.customers (
    customer_id         VARCHAR(32) NOT NULL PRIMARY KEY,   -- one per order (source design)
    customer_unique_id  VARCHAR(32) NOT NULL,                -- the actual person/account
    zip_prefix          VARCHAR(5)  NOT NULL,
    city                VARCHAR(80) NOT NULL,
    state               VARCHAR(2)  NOT NULL
);

CREATE TABLE dw.sellers (
    seller_id   VARCHAR(32) NOT NULL PRIMARY KEY,
    zip_prefix  VARCHAR(5)  NOT NULL,
    city        VARCHAR(80) NOT NULL,
    state       VARCHAR(2)  NOT NULL
);

CREATE TABLE dw.products (
    product_id          VARCHAR(32) NOT NULL PRIMARY KEY,
    category_pt         VARCHAR(80) NOT NULL REFERENCES dw.categories(category_pt),
    name_length         INTEGER,
    description_length  INTEGER,
    photos_qty          INTEGER,
    weight_g            INTEGER,
    length_cm           INTEGER,
    height_cm           INTEGER,
    width_cm            INTEGER
);

CREATE TABLE dw.orders (
    order_id                VARCHAR(32) NOT NULL PRIMARY KEY,
    customer_id             VARCHAR(32) NOT NULL REFERENCES dw.customers(customer_id),
    order_status            VARCHAR(12) NOT NULL,
    purchase_ts             TIMESTAMP   NOT NULL,
    approved_ts             TIMESTAMP,
    delivered_carrier_ts    TIMESTAMP,
    delivered_customer_ts   TIMESTAMP,
    estimated_delivery_date DATE        NOT NULL,
    -- data-quality flags (rows are kept; flags let analysts include/exclude explicitly)
    dq_carrier_before_approval   BOOLEAN NOT NULL,
    dq_delivered_before_carrier  BOOLEAN NOT NULL,
    dq_status_date_conflict      BOOLEAN NOT NULL,  -- delivered w/o date, or canceled with a delivery date
    CHECK (order_status IN ('created','approved','invoiced','processing','shipped',
                            'delivered','canceled','unavailable'))
);

CREATE TABLE dw.order_items (
    order_id         VARCHAR(32)   NOT NULL REFERENCES dw.orders(order_id),
    order_item_id    INTEGER       NOT NULL,
    product_id       VARCHAR(32)   NOT NULL REFERENCES dw.products(product_id),
    seller_id        VARCHAR(32)   NOT NULL REFERENCES dw.sellers(seller_id),
    shipping_limit_ts TIMESTAMP    NOT NULL,
    price            DECIMAL(10,2) NOT NULL CHECK (price > 0),
    freight_value    DECIMAL(10,2) NOT NULL CHECK (freight_value >= 0),
    PRIMARY KEY (order_id, order_item_id)
);

CREATE TABLE dw.payments (
    order_id             VARCHAR(32)   NOT NULL REFERENCES dw.orders(order_id),
    payment_sequential   INTEGER       NOT NULL,
    payment_type         VARCHAR(12)   NOT NULL,
    installments         INTEGER       NOT NULL,
    payment_value        DECIMAL(10,2) NOT NULL CHECK (payment_value >= 0),
    PRIMARY KEY (order_id, payment_sequential)
);

CREATE TABLE dw.reviews (
    review_id        VARCHAR(32) NOT NULL,
    order_id         VARCHAR(32) NOT NULL REFERENCES dw.orders(order_id),
    review_score     INTEGER     NOT NULL CHECK (review_score BETWEEN 1 AND 5),
    has_title        BOOLEAN     NOT NULL,
    has_message      BOOLEAN     NOT NULL,
    creation_date    DATE        NOT NULL,
    answer_ts        TIMESTAMP   NOT NULL,
    PRIMARY KEY (review_id, order_id)   -- review_id alone is NOT unique in the source
);
