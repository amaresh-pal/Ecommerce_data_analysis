#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Rebuild the derived files of the "Olist Clean Order Fact Table" dataset.

    python3 build_olist_dataset.py            # uses ./olist_order_level.csv
    python3 build_olist_dataset.py <dir>      # uses <dir>/olist_order_level.csv

WHAT THIS SCRIPT DOES
---------------------
`olist_order_level.csv` is the primary artefact: it is the **byte-identical output of the
Kaggle run** of the notebook "Olist Data Cleaning: Missing Values and Duplicates"
(https://www.kaggle.com/code/victorzhong0110/olist-data-cleaning-missing-values-and-duplicates).
It is NOT rebuilt here - rebuilding it would mean re-running the join logic, and the point of
this dataset is that every row comes from a Kaggle run.

This script only produces the two *derived* companion files, and both are deterministic
functions of `olist_order_level.csv`:

  * `olist_column_dictionary.csv`  - what every column is and how it was derived.
  * `olist_monthly_summary.csv`    - one row per calendar month.

To rebuild the primary table itself from the raw Olist CSVs, attach the source dataset
`olistbr/brazilian-ecommerce` and run the first code cell of that notebook; it is
self-contained and writes exactly this file.

SOURCE / LICENCE
----------------
Source dataset : https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce
                 ("Brazilian E-Commerce Public Dataset by Olist")
Licence        : CC BY-NC-SA 4.0  (as reported by the Kaggle API on 2026-10-22:
                 `licenseName = "CC BY-NC-SA 4.0"`)
This dataset is released under the SAME licence (CC BY-NC-SA 4.0) so that the
non-commercial and share-alike terms of the source are preserved.
"""
import os
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))

# ------------------------------------------------------------------ the dictionary
# (column, source, derivation_rule, description, gotcha)
COLUMNS = [
    ("order_id", "olist_orders_dataset.csv", "copied as-is",
     "Primary key of this table: one row per order, exactly 99,441 rows.",
     "Unique in this table. In the raw data it is also unique."),
    ("customer_id", "olist_orders_dataset.csv", "copied as-is",
     "The customer identifier the order was placed under.",
     "NOT a person: 2,997 identifiers belong to more than one customer_id."),
    ("customer_unique_id", "olist_customers_dataset.csv",
     "customers.drop_duplicates('customer_id', keep='last').set_index('customer_id')",
     "The person behind the customer_id. Count PEOPLE with this column.",
     "Pseudonymous identifier inherited from the source (a hash). No names, "
     "emails, addresses or phone numbers are included in this dataset."),
    ("customer_state", "olist_customers_dataset.csv", "same join as customer_unique_id",
     "Brazilian state (2-letter code) of the customer's address.",
     "Geographical only - no street address."),
    ("customer_city", "olist_customers_dataset.csv", "same join as customer_unique_id",
     "City of the customer's address.", "Geographical only."),
    ("order_status", "olist_orders_dataset.csv", "copied as-is",
     "Status of the order: delivered, shipped, canceled, unavailable, invoiced, "
     "processing, created, approved.",
     "96,478 orders say 'delivered' but only 96,476 carry a delivery date."),
    ("order_purchase_ts", "olist_orders_dataset.csv",
     "order_purchase_timestamp parsed to datetime",
     "Timestamp of the purchase.", "Never missing."),
    ("order_month", "olist_orders_dataset.csv",
     "order_purchase_ts formatted as %Y-%m",
     "Calendar month of the purchase, e.g. 2017-10. Use it for monthly time series.",
     "Derived from the purchase timestamp, not from the delivery date."),
    ("is_delivered", "olist_orders_dataset.csv",
     "order_delivered_customer_date notna",
     "True when the order actually arrived (a real delivery date exists).",
     "This is a FACT about the data, not the same as order_status == 'delivered' "
     "(8 orders differ)."),
    ("delivery_delay_days", "olist_orders_dataset.csv",
     "(delivered_ts - estimated_delivery_ts) / 86400, NaN unless is_delivered",
     "Days between the promised delivery date and the real delivery. "
     "Negative = arrived EARLY than promised.",
     "NaN for the 2,965 orders that were never delivered - do NOT fillna(0), "
     "that would fake 'delivered exactly on time'."),
    ("item_count", "olist_order_items_dataset.csv",
     "groupby(order_id).order_item_id.nunique()",
     "Number of distinct order items in the order.",
     "The raw items table has NO duplicate rows at all (measured: 0)."),
    ("seller_count", "olist_order_items_dataset.csv",
     "groupby(order_id).seller_id.nunique()",
     "Number of distinct sellers in the order.", "-"),
    ("items_price_sum", "olist_order_items_dataset.csv",
     "groupby(order_id).price.sum()",
     "Sum of the item prices (before freight).",
     "Total item value, NOT the revenue actually collected."),
    ("items_freight_sum", "olist_order_items_dataset.csv",
     "groupby(order_id).freight_value.sum()",
     "Sum of the shipping costs.", "-"),
    ("payment_count", "olist_order_payments_dataset.csv",
     "groupby(order_id).payment_sequential.nunique()",
     "Number of distinct payment records for the order.",
     "2,961 orders have more than one payment row (max 29). This is what makes a "
     "naive merge fan out."),
    ("payment_value_sum", "olist_order_payments_dataset.csv",
     "groupby(order_id).payment_value.sum()",
     "Total amount actually paid for the order. THIS is the revenue number.",
     "Differs from items_price_sum + items_freight_sum by 165,318.88 in total; "
     "the two are not supposed to be identical."),
    ("payment_types", "olist_order_payments_dataset.csv",
     "'|'.join(sorted(set(payment_type)))",
     "Payment methods used, sorted and joined with '|', e.g. 'credit_card|voucher'.",
     "Split on '|' if you need one row per method."),
    ("review_score", "olist_order_reviews_dataset.csv",
     "reviews.sort_values(['order_id','review_score']).drop_duplicates('order_id', keep='last')",
     "The customer's review score, 1-5. NaN when the order has no review.",
     "Collapsed BY ORDER (highest score kept), never by review_id: 789 review_ids "
     "appear on different orders and deduping by review_id would delete 545 orders' "
     "reviews entirely."),
]


def build_dictionary(out_dir):
    rows = []
    for col, src, rule, desc, gotcha in COLUMNS:
        rows.append({"column": col, "source_file": src, "derivation_rule": rule,
                     "description": desc, "gotcha": gotcha})
    path = os.path.join(out_dir, "olist_column_dictionary.csv")
    pd.DataFrame(rows).to_csv(path, index=False)
    return path


def build_monthly(out_dir):
    df = pd.read_csv(os.path.join(out_dir, "olist_order_level.csv"))
    df["is_delivered"] = df["is_delivered"].astype(str).str.lower().isin(["true", "1"])
    df["delivery_delay_days"] = pd.to_numeric(df["delivery_delay_days"], errors="coerce")
    df["payment_value_sum"] = pd.to_numeric(df["payment_value_sum"], errors="coerce")
    df["items_price_sum"] = pd.to_numeric(df["items_price_sum"], errors="coerce")
    df["items_freight_sum"] = pd.to_numeric(df["items_freight_sum"], errors="coerce")
    df["item_count"] = pd.to_numeric(df["item_count"], errors="coerce")
    df["review_score"] = pd.to_numeric(df["review_score"], errors="coerce")

    g = df.groupby("order_month")
    out = pd.DataFrame({
        "n_orders": g.size(),
        "n_delivered": g["is_delivered"].sum(),
        "n_never_delivered": g["is_delivered"].apply(lambda s: int((~s).sum())),
        "n_canceled": g["order_status"].apply(lambda s: int((s == "canceled").sum())),
        "revenue_payment_sum": g["payment_value_sum"].sum(),
        "items_price_sum": g["items_price_sum"].sum(),
        "items_freight_sum": g["items_freight_sum"].sum(),
        "items_sold": g["item_count"].sum(),
        "mean_delivery_delay_days": g["delivery_delay_days"].mean(),
        "median_delivery_delay_days": g["delivery_delay_days"].median(),
        "n_orders_with_review": g["review_score"].count(),
        "mean_review_score": g["review_score"].mean(),
    }).reset_index()
    out["delivered_share"] = out["n_delivered"] / out["n_orders"]
    out["mean_order_value"] = out["revenue_payment_sum"] / out["n_orders"]
    out = out.sort_values("order_month").reset_index(drop=True)
    for c in ("revenue_payment_sum", "items_price_sum", "items_freight_sum"):
        out[c] = out[c].round(2)
    for c in ("mean_delivery_delay_days", "median_delivery_delay_days"):
        out[c] = out[c].round(4)
    out["mean_review_score"] = out["mean_review_score"].round(4)
    path = os.path.join(out_dir, "olist_monthly_summary.csv")
    out.to_csv(path, index=False)
    return path, out


def main(argv):
    out_dir = argv[1] if len(argv) > 1 else HERE
    src = os.path.join(out_dir, "olist_order_level.csv")
    if not os.path.exists(src):
        print("missing %s" % src)
        return 1
    p1 = build_dictionary(out_dir)
    p2, monthly = build_monthly(out_dir)
    print("wrote:", p1)
    print("wrote:", p2, "(%d months)" % len(monthly))
    print()
    print(monthly.head(4).to_string(index=False))
    print("...")
    print(monthly.tail(3).to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
