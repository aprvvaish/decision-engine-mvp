import sqlite3
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

from main import (
    fetch_data,
    compute_indicators,
    buy_signal_from_row,
    momentum_signal_from_row,
    fetch_fundamentals,
    conservative_dcf,
)

DB_FILE = "scan_results.db"
TABLE = "stock_scans"

st.set_page_config(layout="wide")
st.title("🔍 Stock Research")
st.caption("Technicals • Fundamentals • Valuation • Signals")

# =============================
# LOAD ALL AVAILABLE STOCKS
# =============================
@st.cache_data(ttl=600)
def load_all_tickers():
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql(
        f"SELECT DISTINCT ticker FROM {TABLE} ORDER BY ticker",
        conn
    )
    conn.close()
    return df["ticker"].tolist()


all_tickers = load_all_tickers()

if not all_tickers:
    st.error("No stocks found in cache. Run scan first.")
    st.stop()

# =============================
# STOCK SELECTION (FIXED)
# =============================
ticker = st.selectbox(
    "Select a stock",
    options=all_tickers,
    index=0
)

# =============================
# LOAD & SANITIZE PRICE DATA
# =============================
try:
    raw_df = fetch_data(ticker, period="3y")

    # Flatten Yahoo MultiIndex columns
    if isinstance(raw_df.columns, pd.MultiIndex):
        raw_df.columns = raw_df.columns.get_level_values(0)

    raw_df = raw_df[["Open", "High", "Low", "Close", "Volume"]]

except Exception as e:
    st.error(f"Failed to load price data: {e}")
    st.stop()

# =============================
# INDICATORS
# =============================
price_df = compute_indicators(raw_df)

# =============================
# STRATEGY SIGNALS
# =============================
price_df["BUY"] = price_df.apply(buy_signal_from_row, axis=1)
price_df["MOM"] = price_df.apply(momentum_signal_from_row, axis=1)

# =============================
# UNIFIED BUY / SELL / HOLD
# =============================
def unified_signal(row):
    # BUY: strategy-driven
    if row["BUY"] == "BUY" or row["MOM"] == "BUY":
        return "BUY"

    # SELL: trend breakdown
    if (
        row["Close"] < row["SMA_200"]
        and row["SMA_50"] < row["SMA_200"]
    ):
        return "SELL"

    # SELL: euphoria
    if row["RSI"] > 75:
        return "SELL"

    return "HOLD"



price_df["SIGNAL"] = price_df.apply(unified_signal, axis=1)

latest = price_df.iloc[-1]

# =============================
# FUNDAMENTALS + DCF
# =============================
fundamentals = fetch_fundamentals(ticker)
dcf = conservative_dcf(ticker, latest["Close"])

# =============================
# PRICE CHART + SIGNALS
# =============================
st.subheader("📈 Price, Trend & Signals")

fig = go.Figure()

fig.add_trace(go.Scatter(
    x=price_df.index,
    y=price_df["Close"],
    name="Close",
    line=dict(width=2)
))

fig.add_trace(go.Scatter(
    x=price_df.index,
    y=price_df["SMA_50"],
    name="SMA 50",
    line=dict(dash="dot")
))

fig.add_trace(go.Scatter(
    x=price_df.index,
    y=price_df["SMA_200"],
    name="SMA 200",
    line=dict(dash="dash")
))

buy_df = price_df[price_df["SIGNAL"] == "BUY"]
sell_df = price_df[price_df["SIGNAL"] == "SELL"]

fig.add_trace(go.Scatter(
    x=buy_df.index,
    y=buy_df["Close"],
    mode="markers",
    name="BUY",
    marker=dict(color="green", size=9, symbol="triangle-up")
))

fig.add_trace(go.Scatter(
    x=sell_df.index,
    y=sell_df["Close"],
    mode="markers",
    name="SELL",
    marker=dict(color="red", size=9, symbol="triangle-down")
))

fig.update_layout(
    height=450,
    xaxis_title="Date",
    yaxis_title="Price"
)

st.plotly_chart(fig, use_container_width=True)

# =============================
# CURRENT SIGNAL
# =============================
st.subheader("🚦 Current Signal")

signal_icon = {
    "BUY": "🟢",
    "HOLD": "⚪",
    "SELL": "🔴"
}[latest["SIGNAL"]]

st.markdown(f"### {signal_icon} **{latest['SIGNAL']}**")

# =============================
# RSI
# =============================
st.subheader("📉 RSI")

fig_rsi = go.Figure()
fig_rsi.add_trace(go.Scatter(
    x=price_df.index,
    y=price_df["RSI"],
    name="RSI"
))

fig_rsi.add_hline(y=70, line_dash="dash")
fig_rsi.add_hline(y=30, line_dash="dash")

fig_rsi.update_layout(height=260, yaxis_title="RSI")
st.plotly_chart(fig_rsi, use_container_width=True)

# =============================
# FUNDAMENTALS
# =============================
st.subheader("📊 Fundamentals")

c1, c2 = st.columns(2)

with c1:
    st.metric("ROE (%)", f"{fundamentals['roe']}%" if fundamentals["roe"] else "N/A")

with c2:
    st.metric("ROCE (%)", f"{fundamentals['roce']}%" if fundamentals["roce"] else "N/A")

# =============================
# DCF
# =============================
st.subheader("📐 Valuation (Conservative DCF)")

if dcf:
    c1, c2, c3 = st.columns(3)

    with c1:
        st.metric("Intrinsic Value", f"₹ {dcf['intrinsic_value']}")

    with c2:
        st.metric("Margin of Safety", f"{dcf['margin_of_safety_pct']}%")

    with c3:
        st.metric("Growth Assumption", f"{dcf['growth_assumption_pct']}%")
else:
    st.info("DCF not available")

# =============================
# REASONING
# =============================
st.subheader("🧠 Reasoning")

reasons = []

reasons.append(
    ("Price above 200-DMA", "🟢")
    if latest["Close"] > latest["SMA_200"]
    else ("Price below 200-DMA", "🔴")
)

reasons.append(
    ("Unified signal: " + latest["SIGNAL"],
     "🟢" if latest["SIGNAL"] == "BUY"
     else "🔴" if latest["SIGNAL"] == "SELL"
     else "⚪")
)

for text, icon in reasons:
    st.write(f"{icon} {text}")
