# Data dictionary

Source definitions follow the Olist dataset documentation on Kaggle. Derived fields are defined by `sql/load.sql` (DuckDB) and mirrored in `python/olist_ba/clean.py`.

## Layers
| Schema | Purpose |
|---|---|
| `stg` | Raw CSVs loaded 1:1 as text. Never modified. |
| `dw` | Cleaned, typed, keyed model. All analysis reads from `dw`. |

## `dw` tables

### `dw.orders`: one row per order (99,441)
| Column | Type | Key | Description |
|---|---|---|---|
| order_id | VARCHAR(32) | PK | Order identifier |
| customer_id | VARCHAR(32) | FK → customers | **Per-order** customer key. Use `customers.customer_unique_id` to identify a person. |
| order_status | VARCHAR(12) | CHECK | created, approved, invoiced, processing, shipped, delivered, canceled, unavailable |
| purchase_ts | TIMESTAMP | | Order placed |
| approved_ts | TIMESTAMP | | Payment approved (160 NULL) |
| delivered_carrier_ts | TIMESTAMP | | Seller handed the parcel to the carrier (1,783 NULL) |
| delivered_customer_ts | TIMESTAMP | | Delivered to the customer (2,965 NULL) |
| estimated_delivery_date | DATE | | Delivery date promised at purchase |
| dq_carrier_before_approval | BOOLEAN | | Carrier handoff timestamp earlier than approval (1,359) |
| dq_delivered_before_carrier | BOOLEAN | | Customer delivery earlier than carrier handoff (23) |
| dq_status_date_conflict | BOOLEAN | | Delivered without a delivery date, or canceled with one (14) |

### `dw.order_items`: one row per item (112,650), PK (order_id, order_item_id)
| Column | Type | Description |
|---|---|---|
| product_id | FK → products | |
| seller_id | FK → sellers | |
| shipping_limit_ts | TIMESTAMP | Seller's deadline to hand the item to the carrier |
| price | DECIMAL(10,2) | Item price, BRL, > 0 |
| freight_value | DECIMAL(10,2) | Freight charged for the item, BRL, ≥ 0 |

### `dw.payments`: PK (order_id, payment_sequential) (103,886)
payment_type (credit_card, boleto, voucher, debit_card, not_defined), installments, payment_value (BRL).

### `dw.reviews`: PK (review_id, order_id) (99,224)
`review_id` alone is **not** unique in the source (814 duplicates). Columns: review_score (1–5), has_title, has_message (the free text is reduced to flags), creation_date, answer_ts.

### `dw.customers` (99,441) · `dw.sellers` (3,095) · `dw.products` (32,951) · `dw.categories` (74) · `dw.geo_zip` (19,010)
- Zip prefixes are restored to 5 characters with leading zeros.
- Cities are lower-cased and accent-stripped.
- Products: a NULL category becomes `unknown`. The source typo `lenght` is corrected to `length`.
- `categories.is_translated_in_source = FALSE` marks the 3 rows this project added.
- `geo_zip` holds the mean latitude/longitude of the source points inside Brazil's bounding box.

## Analytical views

### `dw.v_order_review`
The latest review per order, by `answer_ts` (tie-break `review_id`). 547 orders have more than one review in the source.

### `dw.v_order_summary`: one row per order (the main analytical grain)
| Column | Definition |
|---|---|
| customer_unique_id, customer_state | From `customers` |
| purchase_date, purchase_month | Date / first day of month of `purchase_ts` |
| in_window | 1 if purchased 2017-01-01 ≤ ts < 2018-09-01 |
| is_revenue_order | 1 unless status is canceled or unavailable |
| is_delivered | 1 if status = delivered **and** a delivery timestamp exists |
| item_count, seller_count | Count of items / distinct sellers |
| product_revenue | Σ item price |
| freight_revenue | Σ freight_value |
| gmv | product_revenue + freight_revenue |
| payment_total, max_installments | Σ payment_value; max instalments |
| approval_hours | purchase → approval, hours |
| seller_to_carrier_days | approval → carrier handoff, days (fractional) |
| carrier_to_customer_days | carrier handoff → delivery, days |
| delivery_days | purchase → delivery, days |
| days_vs_estimate | delivery date − estimated date, whole days (negative = early) |
| is_late | 1 if delivery **date** > estimated date; NULL if not delivered |
| seller_shipped_late | 1 if carrier handoff > the order's latest item shipping limit; NULL if unknown |
| promised_days | estimated date − purchase date, whole days |
| review_score | From `v_order_review` |

Flags are 0/1 integers, not booleans, so the SQL ports to SQL Server.

## BI export (`data/bi/`)
See `dashboard/powerbi/model.md` for the star schema, and `data/bi/manifest.json` (generated) for column lists.
