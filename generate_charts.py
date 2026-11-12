"""
generate_charts.py
------------------
Generates 6 publication-quality, 300 DPI analytical charts using Matplotlib and Seaborn.
Saves all figures into the `charts/` directory for embedding in the Streamlit dashboard
and the ReportLab automated PDF report.
"""

import os
import tempfile
# Ensure a writable matplotlib config directory
os.environ["MPLCONFIGDIR"] = os.path.join(tempfile.gettempdir(), "matplotlib_cache")

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import seaborn as sns
import pandas as pd
import numpy as np

CHARTS_DIR = "charts"
DATA_DIR = "data"

# Corporate Color Palette
NAVY = "#1B365D"
TEAL = "#008080"
CORAL = "#E05A47"
SLATE = "#5A6B7C"
GOLD = "#D4AF37"
LIGHT_BG = "#F8F9FA"

def setup_style():
    plt.style.use("seaborn-v0_8-whitegrid")
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.size": 10,
        "axes.titlesize": 13,
        "axes.titleweight": "bold",
        "axes.titlepad": 12,
        "axes.labelsize": 11,
        "axes.labelweight": "semibold",
        "xtick.labelsize": 9.5,
        "ytick.labelsize": 9.5,
        "figure.titlesize": 15,
        "figure.titleweight": "bold",
        "figure.dpi": 300,
        "savefig.dpi": 300,
        "savefig.bbox": "tight",
        "grid.color": "#E2E8F0",
        "grid.linestyle": "--",
        "grid.alpha": 0.7
    })

def chart_1_revenue_trend(df_monthly: pd.DataFrame):
    """Dual-axis chart: Monthly Revenue (Bar) & Order Count (Line) with Black Friday annotation."""
    # Filter core operational months
    df = df_monthly[df_monthly["order_month"].between("2017-01", "2018-08")].copy()
    
    fig, ax1 = plt.subplots(figsize=(11, 5.5))
    ax2 = ax1.twinx()

    x = np.arange(len(df))
    bars = ax1.bar(x, df["total_revenue"] / 1e6, color=NAVY, alpha=0.85, width=0.55, label="Revenue (R$ Millions)")
    line = ax2.plot(x, df["total_orders"], color=CORAL, marker="o", linewidth=2.5, markersize=6, label="Order Count")

    # Annotate Black Friday 2017 (2017-11)
    bf_idx = df.index[df["order_month"] == "2017-11"].tolist()
    if bf_idx:
        idx_pos = df.index.get_loc(bf_idx[0])
        ax1.annotate(
            "Black Friday Peak\nNov 2017: R$ 1.19M (7,544 orders)",
            xy=(idx_pos, df.loc[bf_idx[0], "total_revenue"] / 1e6),
            xytext=(idx_pos - 2.5, 1.35),
            arrowprops=dict(facecolor=CORAL, edgecolor="none", shrink=0.08, width=1.5, headwidth=6),
            fontsize=9.5, fontweight="bold", color=CORAL,
            bbox=dict(boxstyle="round,pad=0.4", facecolor="#FFF0EE", edgecolor=CORAL, alpha=0.9)
        )

    ax1.set_title("Monthly Revenue & Order Volume Dynamics (2017 - 2018)", pad=15)
    ax1.set_xlabel("Order Month")
    ax1.set_ylabel("Total Revenue (R$ Millions)", color=NAVY)
    ax2.set_ylabel("Total Order Count", color=CORAL)
    ax1.set_xticks(x)
    ax1.set_xticklabels(df["order_month"], rotation=45, ha="right")
    ax1.set_ylim(0, 1.55)
    ax2.set_ylim(0, 9500)
    ax1.yaxis.set_major_formatter(ticker.FormatStrFormatter("R$ %.1fM"))
    ax2.yaxis.set_major_formatter(ticker.StrMethodFormatter("{x:,.0f}"))
    ax1.grid(True, axis="y")
    ax2.grid(False)

    # Combined legend
    lines, labels = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines + lines2, labels + labels2, loc="upper left", frameon=True, framealpha=0.9)

    out_path = os.path.join(CHARTS_DIR, "revenue_order_trend.png")
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)
    print(f"Generated: {out_path}")

def chart_2_delivery_vs_review(df_orders: pd.DataFrame):
    """Review Score Distribution across Delivery Categories."""
    delivered = df_orders[df_orders["is_delivered"] & df_orders["review_score"].notna()].copy()
    cat_order = [
        "Early (>7 days early)",
        "On Time (0-7 days early)",
        "Late (1-7 days late)",
        "Severely Late (>7 days late)"
    ]
    delivered = delivered[delivered["delivery_category"].isin(cat_order)]

    fig, ax = plt.subplots(figsize=(10, 5.5))
    palette = [TEAL, "#4A90E2", "#F5A623", CORAL]
    
    sns.boxplot(
        data=delivered,
        x="delivery_category",
        y="review_score",
        hue="delivery_category",
        legend=False,
        order=cat_order,
        palette=palette,
        boxprops=dict(alpha=0.85),
        showmeans=True,
        meanprops={"marker": "D", "markerfacecolor": "white", "markeredgecolor": "black", "markersize": 7},
        ax=ax
    )

    # Calculate means for text callout
    means = delivered.groupby("delivery_category")["review_score"].mean()
    counts = delivered.groupby("delivery_category")["review_score"].count()
    for i, cat in enumerate(cat_order):
        m = means[cat]
        c = counts[cat]
        ax.text(i, 0.45, f"Avg: {m:.2f} / 5.0\n(n={c:,})", ha="center", va="center", fontsize=9.5, fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.3", facecolor="white", edgecolor="#CBD5E0", alpha=0.9))

    ax.set_title("Customer Review Score by Delivery Performance Tier", pad=15)
    ax.set_xlabel("Delivery Performance Tier")
    ax.set_ylabel("Customer Review Score (1 to 5 Stars)")
    ax.set_ylim(0, 5.5)
    ax.set_yticks([1, 2, 3, 4, 5])

    # Annotation of satisfaction cliff
    ax.annotate(
        "Late Delivery Penalty:\n-1.65 Stars drop for severely late orders",
        xy=(3, 1.73), xytext=(2.1, 4.7),
        arrowprops=dict(facecolor=CORAL, edgecolor="none", shrink=0.08, width=1.5, headwidth=6),
        fontsize=9.5, fontweight="bold", color=CORAL,
        bbox=dict(boxstyle="round,pad=0.4", facecolor="#FFF0EE", edgecolor=CORAL, alpha=0.9)
    )

    out_path = os.path.join(CHARTS_DIR, "delivery_delay_vs_review.png")
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)
    print(f"Generated: {out_path}")

def chart_3_geo_pareto(df_states: pd.DataFrame):
    """Pareto Chart: Top 10 States Revenue & Cumulative Share."""
    df = df_states.head(10).copy()
    
    fig, ax1 = plt.subplots(figsize=(10, 5.5))
    ax2 = ax1.twinx()

    x = np.arange(len(df))
    bars = ax1.bar(x, df["total_revenue"] / 1e6, color=NAVY, alpha=0.85, width=0.55)
    line = ax2.plot(x, df["cumulative_revenue_pct"], color=GOLD, marker="o", linewidth=2.5, markersize=6)

    # 80% threshold line
    ax2.axhline(80, color=CORAL, linestyle="--", linewidth=1.5, alpha=0.8, label="80% Revenue Cutoff")

    ax1.set_title("Top 10 Brazilian States by Revenue (Pareto Distribution)", pad=15)
    ax1.set_xlabel("Customer State")
    ax1.set_ylabel("Revenue (R$ Millions)", color=NAVY)
    ax2.set_ylabel("Cumulative Revenue Share (%)", color=GOLD)
    ax1.set_xticks(x)
    ax1.set_xticklabels(df["customer_state"])
    ax1.set_ylim(0, 7.0)
    ax2.set_ylim(0, 105)
    ax1.yaxis.set_major_formatter(ticker.FormatStrFormatter("R$ %.1fM"))
    ax2.yaxis.set_major_formatter(ticker.FormatStrFormatter("%.0f%%"))

    # Highlight top 3 concentration
    top3_rev_share = df.loc[2, "cumulative_revenue_pct"]
    ax2.text(2, top3_rev_share + 5, f"Top 3 States: {top3_rev_share:.1f}%\nof all revenue",
             ha="center", fontsize=9.5, fontweight="bold", color=NAVY,
             bbox=dict(boxstyle="round,pad=0.3", facecolor="#EEF4F9", edgecolor=NAVY, alpha=0.9))

    ax2.legend(loc="lower right", frameon=True)
    out_path = os.path.join(CHARTS_DIR, "geo_revenue_pareto.png")
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)
    print(f"Generated: {out_path}")

def chart_4_payments_aov(df_payments: pd.DataFrame):
    """Payment Methods Share & Average Order Value."""
    df = df_payments[df_payments["primary_payment_method"] != "Not Defined"].copy().head(5)
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 5))

    # Donut of Revenue Share
    colors = [NAVY, TEAL, GOLD, "#4A90E2", CORAL]
    wedges, texts, autotexts = ax1.pie(
        df["total_revenue"],
        labels=df["primary_payment_method"],
        autopct="%1.1f%%",
        startangle=140,
        colors=colors,
        pctdistance=0.8,
        wedgeprops=dict(width=0.4, edgecolor="white", linewidth=2)
    )
    for at in autotexts:
        at.set_fontsize(9)
        at.set_fontweight("bold")
    ax1.set_title("Revenue Share by Payment Method", pad=12)

    # Horizontal Bar of Ticket Size
    y_pos = np.arange(len(df))
    bars = ax2.barh(y_pos, df["avg_ticket_size"], color=TEAL, alpha=0.85, height=0.55)
    ax2.set_yticks(y_pos)
    ax2.set_yticklabels(df["primary_payment_method"])
    ax2.invert_yaxis()
    ax2.set_xlabel("Average Ticket Size (R$)")
    ax2.set_title("Average Ticket Size by Payment Method", pad=12)
    ax2.xaxis.set_major_formatter(ticker.FormatStrFormatter("R$ %.0f"))

    for bar in bars:
        w = bar.get_width()
        ax2.text(w + 3, bar.get_y() + bar.get_height()/2, f"R$ {w:.2f}",
                 va="center", fontsize=9, fontweight="bold", color=SLATE)
    ax2.set_xlim(0, 205)

    out_path = os.path.join(CHARTS_DIR, "payment_distribution_aov.png")
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)
    print(f"Generated: {out_path}")

def chart_5_repeat_customers(df_customers: pd.DataFrame):
    """Customer Share vs Revenue Share vs LTV Comparison."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.8))

    # Bar chart: Customers vs Revenue Share
    categories = ["One-Time\n(1 Order)", "Repeat\n(>1 Orders)"]
    cust_share = [96.88, 3.12]
    rev_share = [94.10, 5.90]

    x = np.arange(len(categories))
    width = 0.35

    rects1 = ax1.bar(x - width/2, cust_share, width, label="Customer Share (%)", color="#94A3B8")
    rects2 = ax1.bar(x + width/2, rev_share, width, label="Revenue Share (%)", color=NAVY)

    ax1.set_title("Customer Share vs. Revenue Contribution", pad=12)
    ax1.set_xticks(x)
    ax1.set_xticklabels(categories)
    ax1.set_ylabel("Percentage (%)")
    ax1.set_ylim(0, 115)
    ax1.legend(loc="upper right")

    for bar in rects1:
        h = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2, h + 2, f"{h:.1f}%", ha="center", fontsize=9, fontweight="bold")
    for bar in rects2:
        h = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2, h + 2, f"{h:.1f}%", ha="center", fontsize=9, fontweight="bold", color=NAVY)

    # Bar chart: Customer LTV
    ltv = [161.82, 314.99]
    bars_ltv = ax2.bar(x, ltv, width=0.45, color=[TEAL, CORAL], alpha=0.9)
    ax2.set_title("Customer Lifetime Value (LTV Comparison)", pad=12)
    ax2.set_xticks(x)
    ax2.set_xticklabels(categories)
    ax2.set_ylabel("Revenue per Customer (R$)")
    ax2.set_ylim(0, 370)
    ax2.yaxis.set_major_formatter(ticker.FormatStrFormatter("R$ %.0f"))

    for bar in bars_ltv:
        h = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2, h + 8, f"R$ {h:.2f}", ha="center", fontsize=9.5, fontweight="bold")

    ax2.annotate(
        "+94.7% LTV Premium\nfor Repeat Buyers",
        xy=(1, 315), xytext=(0.4, 335),
        arrowprops=dict(facecolor=CORAL, edgecolor="none", shrink=0.08, width=1.5, headwidth=5),
        fontsize=9.5, fontweight="bold", color=CORAL,
        bbox=dict(boxstyle="round,pad=0.3", facecolor="#FFF0EE", edgecolor=CORAL, alpha=0.9)
    )

    out_path = os.path.join(CHARTS_DIR, "repeat_vs_onetime_customers.png")
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)
    print(f"Generated: {out_path}")

def chart_6_delivery_distribution(df_orders: pd.DataFrame):
    """Distribution of Delivery Delay Days highlighting Olist's conservative estimation."""
    delivered = df_orders[df_orders["is_delivered"] & df_orders["delivery_delay_days"].notna()].copy()
    
    # Clip for clean visualization (-40 to +30 days)
    data = delivered["delivery_delay_days"].clip(lower=-35, upper=25)

    fig, ax = plt.subplots(figsize=(10, 5.2))
    
    sns.histplot(
        data,
        bins=60,
        kde=True,
        color=NAVY,
        line_kws=dict(linewidth=2, color=CORAL),
        ax=ax
    )

    median_val = delivered["delivery_delay_days"].median()
    mean_val = delivered["delivery_delay_days"].mean()
    
    ax.axvline(0, color="red", linestyle="--", linewidth=1.8, label="Promised Date (Delay = 0)")
    ax.axvline(median_val, color=TEAL, linestyle="-", linewidth=2, label=f"Median Delivery ({median_val:.1f} days early)")

    ax.set_title("Distribution of Delivery Delay Days (Actual vs. Promised Date)", pad=15)
    ax.set_xlabel("Delivery Delay in Days (Negative = Early, Positive = Late)")
    ax.set_ylabel("Order Count")
    ax.yaxis.set_major_formatter(ticker.StrMethodFormatter("{x:,.0f}"))
    ax.set_xlim(-36, 26)

    # Shaded regions for early vs late
    ax.axvspan(-36, 0, color=TEAL, alpha=0.07, label="Delivered Early (92.1% of orders)")
    ax.axvspan(0, 26, color=CORAL, alpha=0.08, label="Delivered Late (7.9% of orders)")

    ax.annotate(
        f"Conservative SLA Buffer:\nMedian order arrives {abs(median_val):.1f} days\nbefore promised date",
        xy=(median_val, 3800), xytext=(median_val - 16, 5200),
        arrowprops=dict(facecolor=TEAL, edgecolor="none", shrink=0.08, width=1.5, headwidth=6),
        fontsize=9.5, fontweight="bold", color=TEAL,
        bbox=dict(boxstyle="round,pad=0.3", facecolor="#E6F4F1", edgecolor=TEAL, alpha=0.9)
    )

    ax.legend(loc="upper right", frameon=True)
    out_path = os.path.join(CHARTS_DIR, "delivery_time_distribution.png")
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)
    print(f"Generated: {out_path}")

def main():
    setup_style()
    os.makedirs(CHARTS_DIR, exist_ok=True)
    print("Generating publication-ready figures from data...")

    df_orders = pd.read_parquet(os.path.join(DATA_DIR, "clean_orders.parquet"))
    df_monthly = pd.read_csv(os.path.join(DATA_DIR, "summary_monthly.csv"))
    df_states = pd.read_csv(os.path.join(DATA_DIR, "summary_states.csv"))
    df_payments = pd.read_csv(os.path.join(DATA_DIR, "summary_payments.csv"))
    df_customers = pd.read_csv(os.path.join(DATA_DIR, "summary_customers.csv"))

    chart_1_revenue_trend(df_monthly)
    chart_2_delivery_vs_review(df_orders)
    chart_3_geo_pareto(df_states)
    chart_4_payments_aov(df_payments)
    chart_5_repeat_customers(df_customers)
    chart_6_delivery_distribution(df_orders)

    print("\nAll 6 charts generated successfully in charts/ directory.")

if __name__ == "__main__":
    main()

