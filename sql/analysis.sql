-- =============================================================================
-- analysis.sql  |  Business analysis queries (DuckDB; T-SQL port in sql/tsql/)
--
-- Standard scopes (see docs/kpi_dictionary.md):
--   Revenue scope   : in_window = 1 AND is_revenue_order = 1  (excl. canceled/unavailable)
--   Fulfilment scope: in_window = 1 AND is_delivered = 1
--   Window          : purchases 2017-01-01 .. 2018-08-31 (20 complete months)
-- Currency: BRL (R$). "Product revenue" = item price; freight reported separately.
-- Each query is exported by `python -m olist_ba.run_sql` to outputs/sql/analysis/<name>.csv
-- =============================================================================

-- @query q01_kpi_scorecard
-- @question What are the headline commercial and operational KPIs for the analysis window?
WITH w AS (SELECT * FROM dw.v_order_summary WHERE in_window = 1),
rev AS (SELECT * FROM w WHERE is_revenue_order = 1),
dlv AS (SELECT * FROM w WHERE is_delivered = 1)
SELECT
    (SELECT COUNT(*) FROM rev)                                         AS revenue_orders,
    (SELECT ROUND(SUM(product_revenue), 2) FROM rev)                   AS product_revenue,
    (SELECT ROUND(SUM(freight_revenue), 2) FROM rev)                   AS freight_revenue,
    (SELECT ROUND(SUM(product_revenue) / COUNT(*), 2) FROM rev)        AS avg_order_value,
    (SELECT ROUND(SUM(item_count) * 1.0 / COUNT(*), 3) FROM rev)       AS items_per_order,
    (SELECT COUNT(DISTINCT customer_unique_id) FROM rev)               AS unique_customers,
    (SELECT ROUND(SUM(freight_revenue) / SUM(product_revenue), 4) FROM rev) AS freight_to_price_ratio,
    (SELECT ROUND(AVG(CASE WHEN order_status IN ('canceled','unavailable') THEN 1.0 ELSE 0.0 END), 4) FROM w) AS cancel_unavailable_rate,
    (SELECT ROUND(1 - AVG(is_late * 1.0), 4) FROM dlv)                 AS on_time_delivery_rate,
    (SELECT ROUND(AVG(delivery_days), 2) FROM dlv)                     AS avg_delivery_days,
    (SELECT ROUND(AVG(review_score * 1.0), 3) FROM dlv WHERE review_score IS NOT NULL) AS avg_review_score_delivered,
    (SELECT ROUND(AVG(CASE WHEN review_score <= 2 THEN 1.0 ELSE 0.0 END), 4) FROM w WHERE review_score IS NOT NULL) AS low_review_rate;

-- @query q02_monthly_revenue_trend
-- @question How did revenue, orders and AOV evolve month over month?
WITH m AS (
    SELECT purchase_month,
           COUNT(*)                         AS orders,
           SUM(product_revenue)             AS product_revenue,
           SUM(freight_revenue)             AS freight_revenue,
           COUNT(DISTINCT customer_unique_id) AS customers
    FROM dw.v_order_summary
    WHERE in_window = 1 AND is_revenue_order = 1
    GROUP BY purchase_month
)
SELECT purchase_month,
       orders,
       customers,
       ROUND(product_revenue, 2)                                       AS product_revenue,
       ROUND(freight_revenue, 2)                                       AS freight_revenue,
       ROUND(product_revenue / orders, 2)                              AS aov,
       ROUND(100.0 * (product_revenue - LAG(product_revenue) OVER (ORDER BY purchase_month))
             / LAG(product_revenue) OVER (ORDER BY purchase_month), 1)  AS revenue_mom_pct,
       ROUND(AVG(product_revenue) OVER (ORDER BY purchase_month
             ROWS BETWEEN 2 PRECEDING AND CURRENT ROW), 2)              AS revenue_3m_moving_avg,
       ROUND(SUM(product_revenue) OVER (ORDER BY purchase_month
             ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW), 2)      AS cumulative_revenue
FROM m
ORDER BY purchase_month;

-- @query q03_yoy_same_period
-- @question How does Jan-Aug 2018 compare with Jan-Aug 2017, month by month?
WITH m AS (
    SELECT EXTRACT(YEAR FROM purchase_month) AS yr, EXTRACT(MONTH FROM purchase_month) AS mo,
           COUNT(*) AS orders, SUM(product_revenue) AS revenue
    FROM dw.v_order_summary
    WHERE in_window = 1 AND is_revenue_order = 1 AND EXTRACT(MONTH FROM purchase_month) <= 8
    GROUP BY EXTRACT(YEAR FROM purchase_month), EXTRACT(MONTH FROM purchase_month)
)
SELECT cur.mo AS month_num,
       prev.orders AS orders_2017, cur.orders AS orders_2018,
       ROUND(prev.revenue, 2) AS revenue_2017, ROUND(cur.revenue, 2) AS revenue_2018,
       ROUND(100.0 * (cur.revenue - prev.revenue) / prev.revenue, 1) AS revenue_yoy_pct
FROM m cur
JOIN m prev ON prev.mo = cur.mo AND prev.yr = cur.yr - 1
WHERE cur.yr = 2018
UNION ALL
SELECT 99, SUM(CASE WHEN yr = 2017 THEN orders END), SUM(CASE WHEN yr = 2018 THEN orders END),
       ROUND(SUM(CASE WHEN yr = 2017 THEN revenue END), 2), ROUND(SUM(CASE WHEN yr = 2018 THEN revenue END), 2),
       ROUND(100.0 * (SUM(CASE WHEN yr = 2018 THEN revenue END) - SUM(CASE WHEN yr = 2017 THEN revenue END))
             / SUM(CASE WHEN yr = 2017 THEN revenue END), 1)
FROM m
ORDER BY month_num;   -- month_num 99 = Jan-Aug total

-- @query q04_category_pareto
-- @question Which categories drive revenue, and how concentrated is the portfolio (ABC classes)?
WITH c AS (
    SELECT cat.category_en AS category,
           COUNT(DISTINCT i.order_id) AS orders,
           COUNT(*)                   AS units,
           SUM(i.price)               AS revenue,
           AVG(i.price)               AS avg_item_price
    FROM dw.order_items i
    JOIN dw.v_order_summary o ON o.order_id = i.order_id
    JOIN dw.products p        ON p.product_id = i.product_id
    JOIN dw.categories cat    ON cat.category_pt = p.category_pt
    WHERE o.in_window = 1 AND o.is_revenue_order = 1
    GROUP BY cat.category_en
), r AS (
    SELECT *,
           RANK() OVER (ORDER BY revenue DESC) AS revenue_rank,
           SUM(revenue) OVER (ORDER BY revenue DESC ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)
             / SUM(revenue) OVER () AS cumulative_share
    FROM c
)
SELECT revenue_rank, category, orders, units,
       ROUND(revenue, 2) AS revenue,
       ROUND(avg_item_price, 2) AS avg_item_price,
       ROUND(cumulative_share, 4) AS cumulative_share,
       CASE WHEN cumulative_share <= 0.80 THEN 'A'
            WHEN cumulative_share <= 0.95 THEN 'B'
            ELSE 'C' END AS abc_class
FROM r
ORDER BY revenue_rank;

-- @query q05_category_growth
-- @question Which large categories are growing or shrinking (Jan-Aug 2018 vs Jan-Aug 2017)?
WITH c AS (
    SELECT cat.category_en AS category,
           SUM(CASE WHEN o.purchase_month BETWEEN DATE '2017-01-01' AND DATE '2017-08-01' THEN i.price ELSE 0 END) AS rev_2017,
           SUM(CASE WHEN o.purchase_month BETWEEN DATE '2018-01-01' AND DATE '2018-08-01' THEN i.price ELSE 0 END) AS rev_2018
    FROM dw.order_items i
    JOIN dw.v_order_summary o ON o.order_id = i.order_id
    JOIN dw.products p        ON p.product_id = i.product_id
    JOIN dw.categories cat    ON cat.category_pt = p.category_pt
    WHERE o.in_window = 1 AND o.is_revenue_order = 1
    GROUP BY cat.category_en
)
SELECT category,
       ROUND(rev_2017, 2) AS rev_jan_aug_2017,
       ROUND(rev_2018, 2) AS rev_jan_aug_2018,
       ROUND(rev_2018 - rev_2017, 2) AS abs_change,
       ROUND(100.0 * (rev_2018 - rev_2017) / NULLIF(rev_2017, 0), 1) AS growth_pct
FROM c
WHERE rev_2017 + rev_2018 >= 100000          -- material categories only
ORDER BY abs_change DESC;

-- @query q06_state_performance
-- @question How do revenue, freight burden and delivery experience vary by customer state?
SELECT customer_state,
       COUNT(*)                                                    AS orders,
       ROUND(SUM(product_revenue), 2)                              AS product_revenue,
       ROUND(100.0 * SUM(product_revenue) / SUM(SUM(product_revenue)) OVER (), 2) AS revenue_share_pct,
       ROUND(SUM(product_revenue) / COUNT(*), 2)                   AS aov,
       ROUND(SUM(freight_revenue) / SUM(product_revenue), 4)       AS freight_to_price_ratio,
       ROUND(AVG(CASE WHEN is_delivered = 1 THEN delivery_days END), 1) AS avg_delivery_days,
       ROUND(1 - AVG(CASE WHEN is_delivered = 1 THEN is_late * 1.0 END), 4) AS on_time_rate,
       ROUND(AVG(review_score * 1.0), 2)                           AS avg_review,
       RANK() OVER (ORDER BY SUM(product_revenue) DESC)            AS revenue_rank
FROM dw.v_order_summary
WHERE in_window = 1 AND is_revenue_order = 1
GROUP BY customer_state
ORDER BY revenue_rank;

-- @query q07_delivery_vs_review
-- @question How strongly is delivery performance against the promised date associated with review scores?
WITH b AS (
SELECT review_score, CASE WHEN days_vs_estimate <= -15 THEN '1. 15+ days early'
            WHEN days_vs_estimate <= -8  THEN '2. 8-14 days early'
            WHEN days_vs_estimate <= -1  THEN '3. 1-7 days early'
            WHEN days_vs_estimate =  0   THEN '4. On estimated day'
            WHEN days_vs_estimate <= 3   THEN '5. 1-3 days late'
            WHEN days_vs_estimate <= 7   THEN '6. 4-7 days late'
            ELSE                              '7. 8+ days late' END AS delivery_vs_estimate
FROM dw.v_order_summary
WHERE in_window = 1 AND is_delivered = 1 AND review_score IS NOT NULL
)
SELECT delivery_vs_estimate,
       COUNT(*)                                                  AS orders,
       ROUND(AVG(review_score * 1.0), 2)                         AS avg_review,
       ROUND(AVG(CASE WHEN review_score <= 2 THEN 1.0 ELSE 0.0 END), 4) AS low_review_rate,
       ROUND(AVG(CASE WHEN review_score = 5 THEN 1.0 ELSE 0.0 END), 4)  AS five_star_rate
FROM b
GROUP BY delivery_vs_estimate
ORDER BY delivery_vs_estimate;

-- @query q08_fulfilment_stage_trend
-- @question Which fulfilment stage (approval, seller handoff, carrier transit) drives delivery time, and how did it trend?
SELECT purchase_month,
       COUNT(*)                                            AS delivered_orders,
       ROUND(MEDIAN(approval_hours), 1)                    AS median_approval_hours,
       ROUND(MEDIAN(seller_to_carrier_days), 2)            AS median_seller_to_carrier_days,
       ROUND(MEDIAN(carrier_to_customer_days), 2)          AS median_carrier_to_customer_days,
       ROUND(MEDIAN(delivery_days), 2)                     AS median_delivery_days,
       ROUND(AVG(promised_days * 1.0), 1)                  AS avg_promised_days,
       ROUND(AVG(is_late * 1.0), 4)                        AS late_rate
FROM dw.v_order_summary
WHERE in_window = 1 AND is_delivered = 1
  AND dq_carrier_before_approval = FALSE AND dq_delivered_before_carrier = FALSE
GROUP BY purchase_month
ORDER BY purchase_month;

-- @query q09_seller_shipping_sla
-- @question When sellers miss their shipping-limit date, how much does it raise late delivery and low reviews?
WITH b AS (
    SELECT *, CASE WHEN seller_shipped_late = 1 THEN 'Seller missed shipping limit'
                   ELSE 'Seller shipped within limit' END AS seller_handoff
    FROM dw.v_order_summary
    WHERE in_window = 1 AND is_delivered = 1 AND seller_shipped_late IS NOT NULL
)
SELECT seller_handoff,
       COUNT(*)                                          AS delivered_orders,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS share_pct,
       ROUND(AVG(is_late * 1.0), 4)                      AS late_delivery_rate,
       ROUND(AVG(delivery_days), 2)                      AS avg_delivery_days,
       ROUND(AVG(review_score * 1.0), 2)                 AS avg_review,
       ROUND(AVG(CASE WHEN review_score <= 2 THEN 1.0 ELSE 0.0 END), 4) AS low_review_rate
FROM b
GROUP BY seller_handoff
ORDER BY seller_handoff;

-- @query q10_seller_concentration
-- @question How concentrated is revenue across sellers (deciles)?
WITH s AS (
    SELECT i.seller_id, SUM(i.price) AS revenue, COUNT(DISTINCT i.order_id) AS orders
    FROM dw.order_items i
    JOIN dw.v_order_summary o ON o.order_id = i.order_id
    WHERE o.in_window = 1 AND o.is_revenue_order = 1
    GROUP BY i.seller_id
), d AS (
    SELECT *, NTILE(10) OVER (ORDER BY revenue DESC, seller_id) AS revenue_decile FROM s
)
SELECT revenue_decile,
       COUNT(*)                     AS sellers,
       ROUND(SUM(revenue), 2)       AS revenue,
       ROUND(100.0 * SUM(revenue) / SUM(SUM(revenue)) OVER (), 2) AS revenue_share_pct,
       ROUND(MIN(revenue), 2)       AS min_seller_revenue,
       ROUND(MAX(revenue), 2)       AS max_seller_revenue,
       SUM(orders)                  AS orders
FROM d
GROUP BY revenue_decile
ORDER BY revenue_decile;

-- @query q11_seller_risk_scorecard
-- @question Which high-revenue sellers combine poor delivery and poor reviews (account-management priority)?
WITH s AS (
    SELECT i.seller_id,
           MAX(sel.state)                                   AS seller_state,
           COUNT(DISTINCT o.order_id)                       AS orders,
           SUM(i.price)                                     AS revenue,
           AVG(CASE WHEN o.is_delivered = 1 THEN o.is_late * 1.0 END) AS late_rate,
           AVG(CASE WHEN o.is_delivered = 1 THEN o.seller_shipped_late * 1.0 END) AS seller_sla_miss_rate,
           AVG(o.review_score * 1.0)                        AS avg_review
    FROM dw.order_items i
    JOIN dw.v_order_summary o ON o.order_id = i.order_id
    JOIN dw.sellers sel       ON sel.seller_id = i.seller_id
    WHERE o.in_window = 1 AND o.is_revenue_order = 1
    GROUP BY i.seller_id
    HAVING COUNT(DISTINCT o.order_id) >= 50
)
SELECT DENSE_RANK() OVER (ORDER BY revenue DESC) AS revenue_rank,
       seller_id, seller_state, orders,
       ROUND(revenue, 2)               AS revenue,
       ROUND(late_rate, 4)             AS late_rate,
       ROUND(seller_sla_miss_rate, 4)  AS seller_sla_miss_rate,
       ROUND(avg_review, 2)            AS avg_review,
       CASE WHEN avg_review < 3.8 AND late_rate > 0.10 THEN 'High risk'
            WHEN avg_review < 4.0 OR  late_rate > 0.10 THEN 'Watch'
            ELSE 'Healthy' END         AS risk_tier
FROM s
ORDER BY revenue DESC;

-- @query q12_customer_frequency
-- @question What share of customers ever buy more than once?
WITH c AS (
    SELECT customer_unique_id, COUNT(*) AS orders, SUM(product_revenue) AS revenue
    FROM dw.v_order_summary
    WHERE in_window = 1 AND is_revenue_order = 1
    GROUP BY customer_unique_id
), b AS (
    SELECT *, CASE WHEN orders = 1 THEN '1 order' WHEN orders = 2 THEN '2 orders' ELSE '3+ orders' END AS frequency_band
    FROM c
)
SELECT frequency_band,
       COUNT(*)                                                   AS customers,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2)         AS customer_share_pct,
       ROUND(SUM(revenue), 2)                                     AS revenue,
       ROUND(100.0 * SUM(revenue) / SUM(SUM(revenue)) OVER (), 2) AS revenue_share_pct,
       ROUND(AVG(revenue), 2)                                     AS revenue_per_customer
FROM b
GROUP BY frequency_band
ORDER BY frequency_band;

-- @query q13_cohort_retention
-- @question Of customers acquired each month, how many return in later months?
WITH o AS (
    SELECT customer_unique_id, purchase_month
    FROM dw.v_order_summary
    WHERE in_window = 1 AND is_revenue_order = 1
), first_m AS (
    SELECT customer_unique_id, MIN(purchase_month) AS cohort_month FROM o GROUP BY customer_unique_id
), act AS (
    SELECT DISTINCT f.cohort_month, o.customer_unique_id,
           DATE_DIFF('month', f.cohort_month, o.purchase_month) AS months_since_first
    FROM o JOIN first_m f ON f.customer_unique_id = o.customer_unique_id
)
SELECT cohort_month,
       COUNT(DISTINCT CASE WHEN months_since_first = 0 THEN customer_unique_id END) AS cohort_size,
       COUNT(DISTINCT CASE WHEN months_since_first BETWEEN 1 AND 3 THEN customer_unique_id END) AS returned_m1_m3,
       COUNT(DISTINCT CASE WHEN months_since_first >= 1 THEN customer_unique_id END)           AS returned_any_later,
       ROUND(1.0 * COUNT(DISTINCT CASE WHEN months_since_first BETWEEN 1 AND 3 THEN customer_unique_id END)
             / COUNT(DISTINCT CASE WHEN months_since_first = 0 THEN customer_unique_id END), 4) AS retention_m1_m3
FROM act
GROUP BY cohort_month
ORDER BY cohort_month;

-- @query q14_first_delivery_vs_repeat
-- @question Are customers whose first order arrived late less likely to buy again?
WITH ranked AS (
    SELECT customer_unique_id, is_late, review_score, purchase_ts,
           ROW_NUMBER() OVER (PARTITION BY customer_unique_id ORDER BY purchase_ts, order_id) AS order_seq,
           COUNT(*)     OVER (PARTITION BY customer_unique_id)                       AS total_orders
    FROM dw.v_order_summary
    WHERE in_window = 1 AND is_revenue_order = 1
), b AS (
    SELECT *, CASE WHEN is_late = 1 THEN 'First order late' ELSE 'First order on time' END AS first_order_experience
    FROM ranked
    WHERE order_seq = 1 AND is_late IS NOT NULL
      AND purchase_ts < TIMESTAMP '2018-06-01'   -- allow >= 3 months for a repeat purchase to occur
)
SELECT first_order_experience,
       COUNT(*)                                                       AS customers,
       SUM(CASE WHEN total_orders > 1 THEN 1 ELSE 0 END)              AS repeat_customers,
       ROUND(AVG(CASE WHEN total_orders > 1 THEN 1.0 ELSE 0.0 END), 4) AS repeat_rate,
       ROUND(AVG(review_score * 1.0), 2)                              AS avg_first_review
FROM b
GROUP BY first_order_experience
ORDER BY first_order_experience;

-- @query q15_rfm_segments
-- @question How can the customer base be segmented for targeted marketing (RFM)?
WITH c AS (
    SELECT customer_unique_id,
           DATE_DIFF('day', MAX(purchase_date), DATE '2018-09-01') AS recency_days,
           COUNT(*)              AS frequency,
           SUM(product_revenue)  AS monetary
    FROM dw.v_order_summary
    WHERE in_window = 1 AND is_revenue_order = 1
    GROUP BY customer_unique_id
), s AS (
    SELECT *,
           NTILE(5) OVER (ORDER BY recency_days DESC, customer_unique_id) AS r_score,   -- 5 = most recent; id = deterministic tie-break
           NTILE(5) OVER (ORDER BY monetary ASC, customer_unique_id)      AS m_score,   -- 5 = highest spend
           CASE WHEN frequency >= 3 THEN 5 WHEN frequency = 2 THEN 3 ELSE 1 END AS f_score
    FROM c
), seg AS (
    SELECT *,
           CASE WHEN f_score >= 3 AND r_score >= 4                 THEN 'Loyal - active'
                WHEN f_score >= 3                                  THEN 'Loyal - lapsing'
                WHEN r_score >= 4 AND m_score >= 4                 THEN 'New high-value'
                WHEN r_score >= 4                                  THEN 'New standard'
                WHEN r_score <= 2 AND m_score >= 4                 THEN 'Lapsed high-value'
                ELSE                                                    'Lapsed standard' END AS segment
    FROM s
)
SELECT segment,
       COUNT(*)                                                   AS customers,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2)         AS customer_share_pct,
       ROUND(SUM(monetary), 2)                                    AS revenue,
       ROUND(100.0 * SUM(monetary) / SUM(SUM(monetary)) OVER (), 2) AS revenue_share_pct,
       ROUND(AVG(monetary), 2)                                    AS avg_revenue,
       ROUND(AVG(recency_days * 1.0), 0)                          AS avg_recency_days,
       ROUND(AVG(frequency * 1.0), 2)                             AS avg_frequency
FROM seg
GROUP BY segment
ORDER BY revenue DESC;

-- @query q16_payment_mix
-- @question How do customers pay, and do instalment orders carry higher order values?
WITH p AS (
    SELECT p.payment_type,
           COUNT(DISTINCT p.order_id)       AS orders,
           SUM(p.payment_value)             AS payment_value,
           AVG(p.installments * 1.0)        AS avg_installments
    FROM dw.payments p
    JOIN dw.v_order_summary o ON o.order_id = p.order_id
    WHERE o.in_window = 1 AND o.is_revenue_order = 1
    GROUP BY p.payment_type
)
SELECT payment_type, orders,
       ROUND(payment_value, 2) AS payment_value,
       ROUND(100.0 * payment_value / SUM(payment_value) OVER (), 2) AS value_share_pct,
       ROUND(avg_installments, 2) AS avg_installments
FROM p
ORDER BY payment_value DESC;

-- @query q17_installments_vs_aov
-- @question Is order value higher when customers split payments into instalments?
WITH b AS (
    SELECT product_revenue,
           CASE WHEN max_installments <= 1 THEN '1 (single payment)'
                WHEN max_installments <= 3 THEN '2-3'
                WHEN max_installments <= 6 THEN '4-6'
                ELSE '7+' END AS installment_band
    FROM dw.v_order_summary
    WHERE in_window = 1 AND is_revenue_order = 1 AND max_installments IS NOT NULL
)
SELECT installment_band,
       COUNT(*)                                   AS orders,
       ROUND(AVG(product_revenue), 2)             AS aov,
       ROUND(MEDIAN(product_revenue), 2)          AS median_order_value,
       ROUND(100.0 * SUM(product_revenue) / SUM(SUM(product_revenue)) OVER (), 2) AS revenue_share_pct
FROM b
GROUP BY installment_band
ORDER BY installment_band;

-- @query q18_freight_burden_by_price_band
-- @question For which price bands is freight a large share of what the customer pays, and does it hurt reviews?
WITH item_orders AS (
    SELECT o.order_id, o.product_revenue, o.freight_revenue, o.review_score,
           CASE WHEN o.product_revenue < 50  THEN '1. < R$50'
                WHEN o.product_revenue < 100 THEN '2. R$50-99'
                WHEN o.product_revenue < 200 THEN '3. R$100-199'
                WHEN o.product_revenue < 500 THEN '4. R$200-499'
                ELSE '5. R$500+' END AS price_band
    FROM dw.v_order_summary o
    WHERE o.in_window = 1 AND o.is_revenue_order = 1 AND o.item_count > 0
)
SELECT price_band,
       COUNT(*)                                             AS orders,
       ROUND(SUM(product_revenue), 2)                       AS product_revenue,
       ROUND(SUM(freight_revenue) / SUM(product_revenue), 4) AS freight_to_price_ratio,
       ROUND(AVG(freight_revenue), 2)                       AS avg_freight,
       ROUND(AVG(review_score * 1.0), 2)                    AS avg_review
FROM item_orders
GROUP BY price_band
ORDER BY price_band;

-- @query q19_intra_vs_interstate
-- @question How much faster and cheaper are orders fulfilled by sellers in the customer's own state?
WITH ord AS (
    SELECT o.order_id, o.customer_state, o.delivery_days, o.is_late, o.review_score,
           o.freight_revenue, o.product_revenue,
           MIN(CASE WHEN s.state = o.customer_state THEN 1 ELSE 0 END) AS all_sellers_same_state
    FROM dw.v_order_summary o
    JOIN dw.order_items i ON i.order_id = o.order_id
    JOIN dw.sellers s     ON s.seller_id = i.seller_id
    WHERE o.in_window = 1 AND o.is_delivered = 1
    GROUP BY o.order_id, o.customer_state, o.delivery_days, o.is_late, o.review_score,
             o.freight_revenue, o.product_revenue
), b AS (
    SELECT *, CASE WHEN all_sellers_same_state = 1 THEN 'Intrastate' ELSE 'Interstate' END AS route_type
    FROM ord
)
SELECT route_type,
       COUNT(*)                                              AS delivered_orders,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2)    AS share_pct,
       ROUND(AVG(delivery_days), 2)                          AS avg_delivery_days,
       ROUND(AVG(is_late * 1.0), 4)                          AS late_rate,
       ROUND(SUM(freight_revenue) / SUM(product_revenue), 4) AS freight_to_price_ratio,
       ROUND(AVG(review_score * 1.0), 2)                     AS avg_review
FROM b
GROUP BY route_type
ORDER BY route_type;

-- @query q20_weekday_demand
-- @question On which weekdays and hours do orders arrive (capacity planning for approval/support teams)?
WITH b AS (
SELECT ISODOW(purchase_ts)                       AS iso_weekday,   -- 1 = Monday
       CASE WHEN EXTRACT(HOUR FROM purchase_ts) < 6  THEN '00-05'
            WHEN EXTRACT(HOUR FROM purchase_ts) < 12 THEN '06-11'
            WHEN EXTRACT(HOUR FROM purchase_ts) < 18 THEN '12-17'
            ELSE '18-23' END                     AS hour_block
FROM dw.v_order_summary
WHERE in_window = 1 AND is_revenue_order = 1
)
SELECT iso_weekday, hour_block,
       COUNT(*)                                  AS orders,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS share_pct
FROM b
GROUP BY iso_weekday, hour_block
ORDER BY iso_weekday, hour_block;
