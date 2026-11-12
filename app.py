"""
app.py
------
Interactive Streamlit Executive Dashboard for Olist Brazilian E-Commerce Data Analysis.
Provides real-time interactive slicing, KPI scorecards, multi-tab operational analytics,
and an integrated SQL query console connected to `data/olist_analytics.db`.
"""

import os
import sqlite3
import pandas as pd
import numpy as np
import streamlit as st
import altair as alt

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Olist E-Commerce Executive Intelligence",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CUSTOM CSS STYLING ---
st.markdown("""
<style>
    /* Metric Card Styling */
    div[data-testid="stMetric"] {
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        padding: 14px 18px;
        border-radius: 10px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    div[data-testid="stMetricLabel"] {
        font-size: 0.85rem;
        font-weight: 600;
        color: #475569;
    }
    div[data-testid="stMetricValue"] {
        font-size: 1.6rem;
        font-weight: 700;
        color: #1E293B;
    }
    /* Section Headings */
    h1, h2, h3 {
        color: #0F172A;
        font-weight: 700;
    }
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 48px;
        white-space: pre-wrap;
        border-radius: 6px 6px 0 0;
        padding: 8px 16px;
        font-weight: 600;
    }
    /* Info Box */
    .highlight-card {
        background-color: #F0FDF4;
        border-left: 4px solid #16A34A;
        padding: 12px 16px;
        border-radius: 4px;
        margin-bottom: 16px;
        font-size: 0.95rem;
    }
    .warning-card {
        background-color: #FEF2F2;
        border-left: 4px solid #DC2626;
        padding: 12px 16px;
        border-radius: 4px;
        margin-bottom: 16px;
        font-size: 0.95rem;
    }
</style>
""", unsafe_allow_html=True)

DATA_PATH = "data/clean_orders.parquet"
DB_PATH = "data/olist_analytics.db"

# --- CACHED DATA LOADING ---
@st.cache_data
def load_data():
    if not os.path.exists(DATA_PATH):
        import data_cleaning
        data_cleaning.clean_and_prepare_data()
    df = pd.read_parquet(DATA_PATH)
    df["order_purchase_ts"] = pd.to_datetime(df["order_purchase_ts"])
    df["purchase_date"] = pd.to_datetime(df["purchase_date"])
    return df

@st.cache_data
def get_monthly_summary():
    path = "data/summary_monthly.csv"
    if os.path.exists(path):
        return pd.read_csv(path)
    return None

df_raw = load_data()

# --- SIDEBAR CONTROLS ---
st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/4/4b/Olist_Logo.png", width=140)
st.sidebar.title("Navigation & Filters")
st.sidebar.markdown("---")

# 1. Date Range Filter
min_date = df_raw["purchase_date"].min().date()
max_date = df_raw["purchase_date"].max().date()
# Default to active operating window (2017-01-01 to 2018-08-31)
default_start = pd.to_datetime("2017-01-01").date()
default_end = pd.to_datetime("2018-08-31").date()

date_range = st.sidebar.date_input(
    "Purchase Date Range",
    value=(default_start, default_end),
    min_value=min_date,
    max_value=max_date
)

if isinstance(date_range, tuple) and len(date_range) == 2:
    start_dt, end_dt = date_range
else:
    start_dt, end_dt = default_start, default_end

# 2. State Filter
all_states = sorted(df_raw["customer_state"].unique().tolist())
selected_states = st.sidebar.multiselect(
    "Customer State (UF)",
    options=all_states,
    default=[]
)

# 3. Order Status Filter
all_statuses = sorted(df_raw["order_status"].unique().tolist())
selected_statuses = st.sidebar.multiselect(
    "Order Status",
    options=all_statuses,
    default=["delivered"]
)

# 4. Delivery SLA Filter
sla_filter = st.sidebar.radio(
    "Delivery SLA Category",
    options=["All Orders", "Delivered Early / On-Time", "Delivered Late", "Undelivered Only"],
    index=0
)

st.sidebar.markdown("---")
st.sidebar.caption("📊 **Olist Fact Table**: 99,441 verified orders.")
st.sidebar.caption("🔒 **Revenue Reconciliation**: Verified payment collected matches Kaggle benchmark.")

# --- DATA FILTERING LOGIC ---
mask = (df_raw["purchase_date"].dt.date >= start_dt) & (df_raw["purchase_date"].dt.date <= end_dt)

if selected_states:
    mask &= df_raw["customer_state"].isin(selected_states)

if selected_statuses:
    mask &= df_raw["order_status"].isin(selected_statuses)

if sla_filter == "Delivered Early / On-Time":
    mask &= (df_raw["is_delivered"] == True) & (df_raw["delivery_delay_days"] <= 0)
elif sla_filter == "Delivered Late":
    mask &= (df_raw["is_delivered"] == True) & (df_raw["delivery_delay_days"] > 0)
elif sla_filter == "Undelivered Only":
    mask &= (df_raw["is_delivered"] == False)

df_filtered = df_raw[mask].copy()

# --- MAIN DASHBOARD HEADER ---
st.title("🛒 Olist Brazilian E-Commerce Executive Intelligence")
st.markdown(f"**Analysis Window**: `{start_dt}` to `{end_dt}` | **Filtered Orders**: `{len(df_filtered):,}` of `{len(df_raw):,}`")

# --- TOP KPI SCORECARD ---
col1, col2, col3, col4, col5, col6 = st.columns(6)

filtered_rev = df_filtered["payment_value_sum"].sum()
total_orders = len(df_filtered)
aov = filtered_rev / total_orders if total_orders > 0 else 0
unique_cust = df_filtered["customer_unique_id"].nunique()
repeat_rate = (df_filtered["customer_order_count"] > 1).sum() / total_orders * 100 if total_orders > 0 else 0

delivered_subset = df_filtered[df_filtered["is_delivered"]]
ontime_rate = (delivered_subset["delivery_delay_days"] <= 0).mean() * 100 if len(delivered_subset) > 0 else 0
avg_review = df_filtered["review_score"].dropna().mean()

col1.metric("Total Revenue", f"R$ {filtered_rev/1e6:.2f}M" if filtered_rev >= 1e6 else f"R$ {filtered_rev:,.0f}")
col2.metric("Total Orders", f"{total_orders:,}")
col3.metric("Average Order Value", f"R$ {aov:.2f}")
col4.metric("Unique Customers", f"{unique_cust:,}")
col5.metric("On-Time SLA", f"{ontime_rate:.1f}%")
col6.metric("Avg Review Score", f"{avg_review:.2f} ★" if not np.isnan(avg_review) else "N/A")

st.markdown("---")

# --- TABS INTERFACE ---
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📈 Executive Overview & Trends",
    "🚚 Logistics & SLA Impact",
    "👥 Customer & Geo Dynamics",
    "💳 Payments & Baskets",
    "🔍 SQL Analytical Console"
])

# ====================================================================
# TAB 1: EXECUTIVE OVERVIEW & TRENDS
# ====================================================================
with tab1:
    st.subheader("Monthly Sales Velocity & Revenue Growth")
    
    monthly_grp = df_filtered.groupby("order_month").agg(
        revenue=("payment_value_sum", "sum"),
        orders=("order_id", "count"),
        avg_ticket=("payment_value_sum", "mean"),
        avg_rating=("review_score", "mean")
    ).reset_index()

    if len(monthly_grp) > 1:
        monthly_grp["rev_millions"] = monthly_grp["revenue"] / 1e6

        # Altair Dual Axis Chart
        base = alt.Chart(monthly_grp).encode(x=alt.X("order_month:N", title="Order Month", axis=alt.Axis(labelAngle=-45)))
        bars = base.mark_bar(color="#1B365D", opacity=0.85).encode(
            y=alt.Y("rev_millions:Q", title="Revenue (R$ Millions)", axis=alt.Axis(titleColor="#1B365D")),
            tooltip=[
                alt.Tooltip("order_month:N", title="Month"),
                alt.Tooltip("revenue:Q", format="$,.2f", title="Revenue"),
                alt.Tooltip("orders:Q", format=",", title="Orders"),
                alt.Tooltip("avg_ticket:Q", format="$,.2f", title="AOV")
            ]
        )
        line = base.mark_line(color="#E05A47", strokeWidth=3, point=alt.OverlayMarkDef(color="#E05A47")).encode(
            y=alt.Y("orders:Q", title="Total Orders", axis=alt.Axis(titleColor="#E05A47", orient="right")),
            tooltip=[
                alt.Tooltip("order_month:N", title="Month"),
                alt.Tooltip("orders:Q", format=",", title="Orders")
            ]
        )
        chart_trend = alt.layer(bars, line).resolve_scale(y="independent").properties(height=380)
        st.altair_chart(chart_trend, use_container_width=True)
    else:
        st.info("Insufficient monthly data points in the selected filter range.")

    st.markdown("### Operational Day & Hour Demand Patterns")
    c1, c2 = st.columns(2)
    with c1:
        day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        dow_grp = df_filtered.groupby("purchase_day_name")["order_id"].count().reindex(day_order).reset_index()
        dow_chart = alt.Chart(dow_grp).mark_bar(color="#008080").encode(
            x=alt.X("purchase_day_name:N", sort=day_order, title="Day of Week"),
            y=alt.Y("order_id:Q", title="Order Volume"),
            tooltip=["purchase_day_name", "order_id"]
        ).properties(height=280)
        st.altair_chart(dow_chart, use_container_width=True)
    with c2:
        hour_grp = df_filtered.groupby("purchase_hour")["order_id"].count().reset_index()
        hour_chart = alt.Chart(hour_grp).mark_area(color="#5A6B7C", opacity=0.6).encode(
            x=alt.X("purchase_hour:Q", title="Hour of Day (24h)"),
            y=alt.Y("order_id:Q", title="Order Volume"),
            tooltip=["purchase_hour", "order_id"]
        ).properties(height=280)
        st.altair_chart(hour_chart, use_container_width=True)

# ====================================================================
# TAB 2: LOGISTICS & SLA IMPACT
# ====================================================================
with tab2:
    st.subheader("Logistics Performance & Customer Satisfaction Decay")
    
    deliv_only = df_filtered[df_filtered["is_delivered"] & df_filtered["review_score"].notna()]
    
    st.markdown("""
    <div class="warning-card">
        <strong>Critical Finding:</strong> Delivery delays have an immediate, severe penalty on customer satisfaction. 
        Orders arriving on-time or early average <strong>4.22 Stars</strong>, while orders arriving late drop precipitously to 
        <strong>2.57 Stars</strong> (-1.65 rating drop), with severely late orders (>7 days late) averaging only <strong>1.73 Stars</strong>.
    </div>
    """, unsafe_allow_html=True)

    c1, c2 = st.columns([3, 2])
    with c1:
        cat_order = ["Early (>7 days early)", "On Time (0-7 days early)", "Late (1-7 days late)", "Severely Late (>7 days late)"]
        tier_agg = deliv_only.groupby("delivery_category").agg(
            orders=("order_id", "count"),
            avg_review=("review_score", "mean"),
            avg_delay=("delivery_delay_days", "mean")
        ).reindex(cat_order).dropna().reset_index()

        tier_chart = alt.Chart(tier_agg).mark_bar().encode(
            x=alt.X("delivery_category:N", sort=cat_order, title="Delivery Performance Tier"),
            y=alt.Y("avg_review:Q", title="Mean Review Score (1-5)", scale=alt.Scale(domain=[0, 5])),
            color=alt.Color("delivery_category:N", scale=alt.Scale(
                domain=cat_order,
                range=["#008080", "#4A90E2", "#F5A623", "#E05A47"]
            ), legend=None),
            tooltip=[
                alt.Tooltip("delivery_category", title="Tier"),
                alt.Tooltip("avg_review", format=".2f", title="Avg Rating"),
                alt.Tooltip("orders", format=",", title="Orders"),
                alt.Tooltip("avg_delay", format=".1f", title="Avg Delay Days")
            ]
        ).properties(height=340)
        st.altair_chart(tier_chart, use_container_width=True)

    with c2:
        st.markdown("#### Delivery Tier Breakdown Table")
        tier_agg["share_pct"] = (tier_agg["orders"] / tier_agg["orders"].sum() * 100).round(2)
        tier_agg["avg_review"] = tier_agg["avg_review"].round(2)
        tier_agg["avg_delay"] = tier_agg["avg_delay"].round(1)
        st.dataframe(
            tier_agg.rename(columns={
                "delivery_category": "Tier",
                "orders": "Orders",
                "share_pct": "Share %",
                "avg_review": "Avg Review",
                "avg_delay": "Mean Delay (Days)"
            }),
            hide_index=True,
            use_container_width=True
        )

    st.markdown("#### Delivery Delay Days Distribution")
    st.caption("Negative values indicate early arrivals against promised dates. Olist's median buffer is ~12 days early.")
    deliv_clipped = deliv_only[deliv_only["delivery_delay_days"].between(-30, 20)]
    hist_chart = alt.Chart(deliv_clipped).mark_bar(color="#1B365D", opacity=0.7).encode(
        x=alt.X("delivery_delay_days:Q", bin=alt.Bin(maxbins=50), title="Delivery Delay (Days: Negative = Early, Positive = Late)"),
        y=alt.Y("count()", title="Order Count"),
        tooltip=["count()"]
    ).properties(height=260)
    st.altair_chart(hist_chart, use_container_width=True)

# ====================================================================
# TAB 3: CUSTOMER & GEO DYNAMICS
# ====================================================================
with tab3:
    st.subheader("Customer Retention & Geographic Concentration")

    st.markdown("""
    <div class="highlight-card">
        <strong>Retention Alert:</strong> Only <strong>3.12%</strong> of unique customers ever place a repeat order on Olist. 
        However, repeat customers deliver a <strong>+94.7% LTV premium</strong> (R$ 314.99 vs R$ 161.82 per customer), 
        highlighting a massive untapped revenue lever through loyalty and retention marketing.
    </div>
    """, unsafe_allow_html=True)

    col_geo1, col_geo2 = st.columns([3, 2])
    with col_geo1:
        st.markdown("#### Top 10 States by Revenue (Pareto Analysis)")
        state_agg = df_filtered.groupby("customer_state").agg(
            orders=("order_id", "count"),
            revenue=("payment_value_sum", "sum"),
            avg_aov=("payment_value_sum", "mean"),
            avg_rating=("review_score", "mean"),
            freight_ratio=("freight_ratio", "mean")
        ).sort_values("revenue", ascending=False).head(10).reset_index()
        state_agg["rev_millions"] = state_agg["revenue"] / 1e6
        state_agg["freight_pct"] = (state_agg["freight_ratio"] * 100).round(1)

        state_chart = alt.Chart(state_agg).mark_bar(color="#1B365D").encode(
            x=alt.X("customer_state:N", sort="-y", title="State (UF)"),
            y=alt.Y("rev_millions:Q", title="Revenue (R$ Millions)"),
            tooltip=["customer_state", alt.Tooltip("revenue", format="$,.2f"), alt.Tooltip("orders", format=",")]
        ).properties(height=340)
        st.altair_chart(state_chart, use_container_width=True)

    with col_geo2:
        st.markdown("#### State Logistics & Freight Metrics")
        st.dataframe(
            state_agg[["customer_state", "orders", "rev_millions", "freight_pct", "avg_rating"]].rename(columns={
                "customer_state": "State",
                "orders": "Orders",
                "rev_millions": "Revenue (R$ M)",
                "freight_pct": "Freight % of Item",
                "avg_rating": "Avg Rating"
            }),
            hide_index=True,
            use_container_width=True
        )

# ====================================================================
# TAB 4: PAYMENTS & BASKETS
# ====================================================================
with tab4:
    st.subheader("Payment Methods & Order Basket Structure")

    cp1, cp2 = st.columns(2)
    with cp1:
        st.markdown("#### Revenue Share by Payment Method")
        pm_agg = df_filtered[df_filtered["primary_payment_method"] != "Unknown"].groupby("primary_payment_method").agg(
            revenue=("payment_value_sum", "sum"),
            orders=("order_id", "count"),
            avg_ticket=("payment_value_sum", "mean")
        ).sort_values("revenue", ascending=False).head(5).reset_index()

        pie_chart = alt.Chart(pm_agg).mark_arc(innerRadius=60).encode(
            theta=alt.Theta("revenue:Q"),
            color=alt.Color("primary_payment_method:N", title="Payment Method", scale=alt.Scale(scheme="category10")),
            tooltip=["primary_payment_method", alt.Tooltip("revenue", format="$,.2f"), alt.Tooltip("orders", format=",")]
        ).properties(height=320)
        st.altair_chart(pie_chart, use_container_width=True)

    with cp2:
        st.markdown("#### Average Order Value by Payment Method")
        ticket_chart = alt.Chart(pm_agg).mark_bar(color="#008080").encode(
            y=alt.Y("primary_payment_method:N", sort="-x", title="Payment Method"),
            x=alt.X("avg_ticket:Q", title="Average Ticket Size (R$)"),
            tooltip=["primary_payment_method", alt.Tooltip("avg_ticket", format="$,.2f")]
        ).properties(height=320)
        st.altair_chart(ticket_chart, use_container_width=True)

    st.markdown("#### Basket Economics: Order Item Counts")
    item_agg = df_filtered[df_filtered["item_count"].notna()].groupby("item_count").agg(
        orders=("order_id", "count"),
        total_rev=("payment_value_sum", "sum")
    ).head(6).reset_index()
    item_agg["item_label"] = item_agg["item_count"].astype(int).astype(str) + " Items"
    item_chart = alt.Chart(item_agg).mark_bar(color="#5A6B7C").encode(
        x=alt.X("item_label:N", sort=None, title="Item Count in Basket"),
        y=alt.Y("orders:Q", title="Order Count"),
        tooltip=["item_label", "orders"]
    ).properties(height=240)
    st.altair_chart(item_chart, use_container_width=True)

# ====================================================================
# TAB 5: SQL ANALYTICAL CONSOLE
# ====================================================================
with tab5:
    st.subheader("Live SQLite Analytical Console (`data/olist_analytics.db`)")
    st.markdown("Run custom SQL queries directly against the production analytical database.")

    preset_queries = {
        "Monthly Revenue & On-Time Rate": """
SELECT 
    order_month,
    COUNT(order_id) AS orders,
    ROUND(SUM(payment_value_sum), 2) AS revenue,
    ROUND(AVG(payment_value_sum), 2) AS aov,
    ROUND(100.0 * SUM(CASE WHEN is_delivered = 1 AND delivery_delay_days <= 0 THEN 1 ELSE 0 END) / COUNT(order_id), 1) AS on_time_rate_pct
FROM orders
GROUP BY order_month
ORDER BY order_month DESC;
""",
        "Delivery Delay Penalty on Review Ratings": """
SELECT 
    delivery_category,
    COUNT(order_id) AS orders,
    ROUND(AVG(delivery_delay_days), 2) AS mean_delay_days,
    ROUND(AVG(review_score), 3) AS mean_rating,
    ROUND(100.0 * SUM(CASE WHEN review_score >= 4 THEN 1 ELSE 0 END) / COUNT(review_score), 2) AS positive_pct
FROM orders
WHERE is_delivered = 1
GROUP BY delivery_category
ORDER BY mean_delay_days ASC;
""",
        "Repeat vs One-Time Customers LTV": """
SELECT 
    CASE WHEN is_repeat_customer = 1 THEN 'Repeat Buyer' ELSE 'One-Time Buyer' END AS customer_type,
    COUNT(DISTINCT customer_unique_id) AS customers,
    COUNT(order_id) AS orders,
    ROUND(SUM(payment_value_sum), 2) AS total_revenue,
    ROUND(SUM(payment_value_sum) / COUNT(DISTINCT customer_unique_id), 2) AS ltv_per_customer
FROM orders
GROUP BY is_repeat_customer;
""",
        "Top 10 States Freight Burden": """
SELECT 
    customer_state,
    COUNT(order_id) AS total_orders,
    ROUND(SUM(payment_value_sum), 2) AS revenue,
    ROUND(AVG(freight_ratio) * 100, 2) AS avg_freight_pct,
    ROUND(AVG(review_score), 2) AS avg_rating
FROM orders
GROUP BY customer_state
ORDER BY revenue DESC
LIMIT 10;
"""
    }

    selected_preset = st.selectbox("Select a Preset Query or write your own below:", options=list(preset_queries.keys()))
    query_input = st.text_area("SQL Editor", value=preset_queries[selected_preset].strip(), height=160)

    if st.button("Execute SQL Query", type="primary"):
        if not os.path.exists(DB_PATH):
            st.error(f"Database {DB_PATH} not found.")
        else:
            try:
                conn = sqlite3.connect(DB_PATH)
                res_df = pd.read_sql_query(query_input, conn)
                conn.close()
                st.success(f"Query returned {len(res_df):,} rows.")
                st.dataframe(res_df, use_container_width=True)
                
                # CSV Download Button
                csv_bytes = res_df.to_csv(index=False).encode("utf-8")
                st.download_button("Download Result as CSV", data=csv_bytes, file_name="query_result.csv", mime="text/csv")
            except Exception as e:
                st.error(f"SQL Execution Error: {e}")

st.markdown("---")
st.caption("Built with Python, Pandas, Altair, SQLite & Streamlit | Verified against Olist Order Fact Table.")

