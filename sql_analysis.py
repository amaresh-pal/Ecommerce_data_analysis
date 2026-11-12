"""
sql_analysis.py
---------------
Executes production SQL analytical queries against the SQLite analytics database (`data/olist_analytics.db`),
verifies all KPI calculations, prints formatted summaries, and exports tabular data for dashboard and reporting.
"""

import os
import sqlite3
import pandas as pd

DB_PATH = "data/olist_analytics.db"
OUTPUT_DIR = "data"

def run_query(conn: sqlite3.Connection, query: str) -> pd.DataFrame:
    return pd.read_sql_query(query, conn)

def main():
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(f"Database {DB_PATH} not found. Run data_cleaning.py first.")

    conn = sqlite3.connect(DB_PATH)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print("=" * 80)
    print("OLIST E-COMMERCE SQL ANALYTICAL ENGINE")
    print("=" * 80)

    # 1. Monthly Executive Performance
    q_monthly = """
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
    """
    df_monthly = run_query(conn, q_monthly)
    # Calculate MoM revenue growth
    df_monthly["revenue_growth_pct"] = (df_monthly["total_revenue"].pct_change() * 100).round(2)
    df_monthly.to_csv(os.path.join(OUTPUT_DIR, "summary_monthly.csv"), index=False)
    print("\n[1] MONTHLY EXECUTIVE SUMMARY (Sample of 2017-2018):")
    print(df_monthly[df_monthly["order_month"].between("2017-06", "2018-05")][
        ["order_month", "total_orders", "total_revenue", "avg_order_value", "revenue_growth_pct", "avg_review_score"]
    ].to_string(index=False))

    # 2. Customer Retention & Repeat Economics
    q_customers = """
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
    """
    df_customers = run_query(conn, q_customers)
    total_customers = df_customers["unique_customers"].sum()
    total_rev = df_customers["total_revenue"].sum()
    df_customers["customer_share_pct"] = (df_customers["unique_customers"] / total_customers * 100).round(2)
    df_customers["revenue_share_pct"] = (df_customers["total_revenue"] / total_rev * 100).round(2)
    df_customers.to_csv(os.path.join(OUTPUT_DIR, "summary_customers.csv"), index=False)
    print("\n[2] CUSTOMER RETENTION & REPEAT PURCHASE ECONOMICS:")
    print(df_customers.to_string(index=False))

    # 3. Logistics & Customer Satisfaction (Delivery Delay vs Review)
    q_logistics = """
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
    """
    df_logistics = run_query(conn, q_logistics)
    df_logistics.to_csv(os.path.join(OUTPUT_DIR, "summary_logistics.csv"), index=False)
    print("\n[3] LOGISTICS PERFORMANCE & CUSTOMER SATISFACTION:")
    print(df_logistics.to_string(index=False))

    # 4. Geographic State Ranking
    q_states = """
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
    """
    df_states = run_query(conn, q_states)
    df_states["cumulative_revenue_pct"] = df_states["revenue_share_pct"].cumsum().round(2)
    df_states.to_csv(os.path.join(OUTPUT_DIR, "summary_states.csv"), index=False)
    print("\n[4] TOP 10 BRAZILIAN STATES BY REVENUE:")
    print(df_states.head(10).to_string(index=False))

    # 5. Payment Methods Analysis
    q_payments = """
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
    """
    df_payments = run_query(conn, q_payments)
    df_payments.to_csv(os.path.join(OUTPUT_DIR, "summary_payments.csv"), index=False)
    print("\n[5] PAYMENT METHODS DISTRIBUTION & TICKET SIZE:")
    print(df_payments.to_string(index=False))

    conn.close()
    print("\n" + "=" * 80)
    print("SQL analysis completed successfully. Summaries exported to data/ directory.")
    print("=" * 80)

if __name__ == "__main__":
    main()

