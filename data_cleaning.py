"""
data_cleaning.py
----------------
Non-destructive data cleaning and feature engineering pipeline for the Olist E-commerce dataset.
Reads the immutable source `olist_order_level.csv`, validates data integrity, engineers analytical
features, and exports clean data to SQLite (`data/olist_analytics.db`) and Parquet (`data/clean_orders.parquet`).
"""

import os
import sqlite3
import pandas as pd
import numpy as np

def clean_and_prepare_data(input_path: str = "olist_order_level.csv",
                            db_path: str = "data/olist_analytics.db",
                            parquet_path: str = "data/clean_orders.parquet") -> pd.DataFrame:
    print(f"[1/5] Loading raw order fact table from {input_path}...")
    df = pd.read_csv(input_path)
    initial_rows, initial_cols = df.shape
    print(f"      Loaded {initial_rows:,} rows and {initial_cols} columns.")

    print("[2/5] Performing type conversions and validation...")
    # Convert timestamps
    df["order_purchase_ts"] = pd.to_datetime(df["order_purchase_ts"])
    df["purchase_date"] = df["order_purchase_ts"].dt.date
    df["purchase_year"] = df["order_purchase_ts"].dt.year
    df["purchase_year_month"] = df["order_purchase_ts"].dt.to_period("M").astype(str)
    df["purchase_day_name"] = df["order_purchase_ts"].dt.day_name()
    df["purchase_hour"] = df["order_purchase_ts"].dt.hour

    # Boolean flags
    df["is_delivered"] = df["is_delivered"].astype(bool)

    # Numeric conversion with explicit null preservation
    num_cols = [
        "delivery_delay_days", "item_count", "seller_count",
        "items_price_sum", "items_freight_sum", "payment_count",
        "payment_value_sum", "review_score"
    ]
    for col in num_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # String cleaning & normalization
    df["customer_state"] = df["customer_state"].astype(str).str.upper().str.strip()
    df["customer_city"] = df["customer_city"].astype(str).str.title().str.strip()
    df["order_status"] = df["order_status"].astype(str).str.lower().str.strip()
    df["payment_types"] = df["payment_types"].fillna("unknown").astype(str).str.lower().str.strip()

    print("[3/5] Engineering analytical features...")
    # 1. Delivery performance categories
    # Note: delivery_delay_days is (delivered_ts - estimated_ts) in days. Negative = arrived early.
    def categorize_delivery(row):
        if not row["is_delivered"] or pd.isna(row["delivery_delay_days"]):
            return "Undelivered"
        delay = row["delivery_delay_days"]
        if delay <= -7:
            return "Early (>7 days early)"
        elif delay <= 0:
            return "On Time (0-7 days early)"
        elif delay <= 7:
            return "Late (1-7 days late)"
        else:
            return "Severely Late (>7 days late)"

    df["delivery_category"] = df.apply(categorize_delivery, axis=1)
    
    # Binary delay indicator (nullable: True if late, False if on-time/early, None if undelivered)
    df["is_late"] = np.where(
        df["delivery_delay_days"].isna(),
        np.nan,
        df["delivery_delay_days"] > 0
    )

    # 2. Financial ratios
    df["freight_ratio"] = np.where(
        df["items_price_sum"] > 0,
        (df["items_freight_sum"] / df["items_price_sum"]).round(4),
        0.0
    )
    df["price_per_item"] = np.where(
        df["item_count"] > 0,
        (df["items_price_sum"] / df["item_count"]).round(2),
        np.nan
    )

    # 3. Customer order frequency & repeat status
    customer_order_counts = df.groupby("customer_unique_id")["order_id"].transform("count")
    df["customer_order_count"] = customer_order_counts
    df["is_repeat_customer"] = df["customer_order_count"] > 1

    # 4. Primary payment category (first or dominant method)
    def clean_payment_primary(pt):
        if pt == "unknown":
            return "Unknown"
        if "|" in pt:
            return "Multiple Methods (" + pt.replace("|", " + ") + ")"
        return pt.replace("_", " ").title()

    df["primary_payment_method"] = df["payment_types"].apply(clean_payment_primary)

    print("[4/5] Verifying integrity metrics...")
    assert len(df) == initial_rows, f"Row count changed! Expected {initial_rows}, got {len(df)}"
    assert df["order_id"].nunique() == initial_rows, "Duplicate order_id detected!"
    
    total_rev = df["payment_value_sum"].sum()
    print(f"      Verified Total Revenue Collected: R$ {total_rev:,.2f}")
    print(f"      Unique Customers: {df['customer_unique_id'].nunique():,}")
    print(f"      Repeat Customers: {(df['customer_order_count'] > 1).groupby(df['customer_unique_id']).first().sum():,} "
          f"({(df['customer_order_count'] > 1).groupby(df['customer_unique_id']).first().mean()*100:.2f}%)")
    print(f"      Delivered Orders: {df['is_delivered'].sum():,} ({df['is_delivered'].mean()*100:.2f}%)")

    print(f"[5/5] Exporting clean data to Parquet and SQLite...")
    os.makedirs(os.path.dirname(parquet_path), exist_ok=True)
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    # Save to Parquet
    df.to_parquet(parquet_path, index=False)
    print(f"      Saved Parquet: {parquet_path} ({os.path.getsize(parquet_path) / 1024 / 1024:.2f} MB)")

    # Save to SQLite
    # Convert datetime columns to string format for SQLite compatibility
    df_sqlite = df.copy()
    df_sqlite["order_purchase_ts"] = df_sqlite["order_purchase_ts"].astype(str)
    df_sqlite["purchase_date"] = df_sqlite["purchase_date"].astype(str)
    df_sqlite["is_delivered"] = df_sqlite["is_delivered"].astype(int)
    df_sqlite["is_repeat_customer"] = df_sqlite["is_repeat_customer"].astype(int)

    conn = sqlite3.connect(db_path)
    df_sqlite.to_sql("orders", conn, if_exists="replace", index=False)

    # Create helpful indexes for performance
    cursor = conn.cursor()
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_order_id ON orders(order_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_customer_unique_id ON orders(customer_unique_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_customer_state ON orders(customer_state);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_order_month ON orders(order_month);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_is_delivered ON orders(is_delivered);")
    conn.commit()
    conn.close()
    print(f"      Saved SQLite database: {db_path} ({os.path.getsize(db_path) / 1024 / 1024:.2f} MB)")
    print("Data cleaning & persistence completed successfully.\n")
    return df

if __name__ == "__main__":
    clean_and_prepare_data()

