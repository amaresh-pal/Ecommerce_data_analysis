-- ====================================================================
-- Olist E-Commerce Production SQL Analytical Queries
-- Database: SQLite (data/olist_analytics.db)
-- Table: orders (Cleaned Order Fact Table)
-- ====================================================================

-- 1. Monthly Executive Performance (Sales, Volume, AOV, MoM Growth)
-- --------------------------------------------------------------------
SELECT 
    order_month,
    COUNT(order_id) AS total_orders,
    SUM(CASE WHEN is_delivered = 1 THEN 1 ELSE 0 END) AS delivered_orders,
    ROUND(SUM(payment_value_sum), 2) AS total_revenue,
    ROUND(SUM(items_price_sum), 2) AS total_items_value,
    ROUND(SUM(items_freight_sum), 2) AS total_freight_value,
    ROUND(AVG(payment_value_sum), 2) AS avg_order_value,
    ROUND(AVG(review_score), 3) AS avg_review_score,
    ROUND(AVG(CASE WHEN is_delivered = 1 THEN delivery_delay_days ELSE NULL END), 2) AS avg_delivery_delay_days
FROM orders
GROUP BY order_month
ORDER BY order_month ASC;

-- 2. Customer Retention & Repeat Purchase Economics
-- --------------------------------------------------------------------
SELECT 
    CASE WHEN is_repeat_customer = 1 THEN 'Repeat Customer (>1 order)' ELSE 'One-Time Customer (1 order)' END AS customer_segment,
    COUNT(DISTINCT customer_unique_id) AS unique_customers,
    COUNT(order_id) AS total_orders,
    ROUND(SUM(payment_value_sum), 2) AS total_revenue,
    ROUND(AVG(payment_value_sum), 2) AS avg_order_value,
    ROUND(SUM(payment_value_sum) / COUNT(DISTINCT customer_unique_id), 2) AS revenue_per_customer,
    ROUND(AVG(review_score), 3) AS avg_review_score
FROM orders
GROUP BY is_repeat_customer;

-- 3. Logistics Delivery Performance & Customer Satisfaction Impact
-- --------------------------------------------------------------------
SELECT 
    delivery_category,
    COUNT(order_id) AS order_count,
    ROUND(100.0 * COUNT(order_id) / (SELECT COUNT(*) FROM orders WHERE is_delivered = 1), 2) AS pct_of_delivered,
    ROUND(AVG(delivery_delay_days), 2) AS avg_delay_days,
    ROUND(AVG(review_score), 3) AS avg_review_score,
    SUM(CASE WHEN review_score >= 4 THEN 1 ELSE 0 END) AS positive_reviews_count,
    ROUND(100.0 * SUM(CASE WHEN review_score >= 4 THEN 1 ELSE 0 END) / COUNT(review_score), 2) AS positive_review_pct
FROM orders
WHERE is_delivered = 1
GROUP BY delivery_category
ORDER BY avg_delay_days ASC;

-- 4. Geographic State Performance (Sales Concentration, Freight, Ratings)
-- --------------------------------------------------------------------
SELECT 
    customer_state,
    COUNT(order_id) AS total_orders,
    ROUND(100.0 * COUNT(order_id) / (SELECT COUNT(*) FROM orders), 2) AS order_share_pct,
    ROUND(SUM(payment_value_sum), 2) AS total_revenue,
    ROUND(100.0 * SUM(payment_value_sum) / (SELECT SUM(payment_value_sum) FROM orders WHERE payment_value_sum IS NOT NULL), 2) AS revenue_share_pct,
    ROUND(AVG(payment_value_sum), 2) AS avg_order_value,
    ROUND(AVG(freight_ratio) * 100, 2) AS avg_freight_pct_of_price,
    ROUND(AVG(CASE WHEN is_delivered = 1 THEN delivery_delay_days ELSE NULL END), 2) AS avg_delivery_delay_days,
    ROUND(AVG(review_score), 3) AS avg_review_score
FROM orders
GROUP BY customer_state
ORDER BY total_revenue DESC;

-- 5. Payment Method Share & Basket Economics
-- --------------------------------------------------------------------
SELECT 
    primary_payment_method,
    COUNT(order_id) AS order_count,
    ROUND(100.0 * COUNT(order_id) / (SELECT COUNT(*) FROM orders WHERE primary_payment_method != 'Unknown'), 2) AS order_share_pct,
    ROUND(SUM(payment_value_sum), 2) AS total_revenue,
    ROUND(100.0 * SUM(payment_value_sum) / (SELECT SUM(payment_value_sum) FROM orders WHERE payment_value_sum IS NOT NULL), 2) AS revenue_share_pct,
    ROUND(AVG(payment_value_sum), 2) AS avg_ticket_size,
    ROUND(AVG(review_score), 3) AS avg_review_score
FROM orders
WHERE primary_payment_method != 'Unknown'
GROUP BY primary_payment_method
ORDER BY total_revenue DESC;

-- 6. Basket Size & Multi-Seller Marketplace Distribution
-- --------------------------------------------------------------------
SELECT 
    CASE 
        WHEN item_count = 1 THEN '1 Item'
        WHEN item_count = 2 THEN '2 Items'
        WHEN item_count BETWEEN 3 AND 5 THEN '3-5 Items'
        WHEN item_count > 5 THEN '6+ Items'
        ELSE 'Unfulfilled / Zero'
    END AS basket_size_tier,
    COUNT(order_id) AS order_count,
    ROUND(SUM(payment_value_sum), 2) AS total_revenue,
    ROUND(AVG(payment_value_sum), 2) AS avg_order_value,
    ROUND(AVG(seller_count), 2) AS avg_sellers_per_order,
    ROUND(AVG(review_score), 3) AS avg_review_score
FROM orders
GROUP BY basket_size_tier
ORDER BY total_revenue DESC;

