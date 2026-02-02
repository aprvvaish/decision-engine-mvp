import sqlite3
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from datetime import date

from main import build_portfolio_equity_curve

DB_FILE = "scan_results.db"
TABLE = "stock_scans"

st.set_page_config(layout="wide")
st.title("🧪 Portfolio Simulator")
st.caption("Allocation → Experience → Insight")


# =============================
# HELPERS
# =============================
def fmt_date(d):
    if d is None or pd.isna(d):
        return "—"
    return d.date()


# =============================
# LOAD DATA
# =============================
@st.cache_data(ttl=300)
def load_latest():
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql(
        f"""
        SELECT *
        FROM {TABLE}
        WHERE scan_timestamp = (
            SELECT MAX(scan_timestamp) FROM {TABLE}
        )
        """,
        conn
    )
    conn.close()
    return df


df = load_latest()

# =============================
# INPUTS
# =============================
capital = st.number_input(
    "Initial Capital (₹)",
    min_value=100_000,
    step=50_000,
    value=500_000
)

max_weight = st.slider(
    "Max allocation per stock (%)",
    5, 40, 25
)

start_date = st.date_input(
    "Simulation start date",
    value=date.today().replace(year=date.today().year - 3)
)

# =============================
# ALLOCATION
# =============================
df = df.sort_values("buy_sharpe", ascending=False)

weights = []
remaining = 1.0

for _ in df.itertuples():
    if remaining <= 0:
        weights.append(0)
    else:
        w = min(max_weight / 100, remaining)
        weights.append(w)
        remaining -= w

df["weight"] = weights
df = df[df["weight"] > 0]

df["allocation"] = df["weight"] * capital
df["shares"] = (df["allocation"] / df["price"]).astype(int)

st.subheader("📋 Simulated Holdings")
st.dataframe(
    df[["ticker", "weight", "allocation", "shares", "buy_sharpe"]],
    use_container_width=True
)

if remaining > 0:
    st.info(f"{remaining*100:.1f}% capital left as cash")

# =============================
# EXPERIENCE VIEW
# =============================
st.divider()
st.subheader("📈 Portfolio Experience")
st.caption("Buy-and-hold • No rebalancing • Cash stays flat")

if st.button("▶ Simulate Portfolio Over Time"):
    tickers = df["ticker"].tolist()
    weights_map = dict(zip(df["ticker"], df["weight"]))

    with st.spinner("Building portfolio equity curve..."):
        result = build_portfolio_equity_curve(
            tickers=tickers,
            weights=weights_map,
            initial_capital=capital,
            start_date=str(start_date)
        )

    equity = result["equity_curve"]
    drawdown = result["drawdown"]

    # -----------------------------
    # EQUITY CURVE
    # -----------------------------
    st.subheader("💰 Portfolio Value Over Time")

    fig_eq = go.Figure()
    fig_eq.add_trace(go.Scatter(
        x=equity.index,
        y=equity.values,
        name="Portfolio Value"
    ))

    fig_eq.update_layout(
        height=420,
        yaxis_title="Value (₹)",
        xaxis_title="Date"
    )

    st.plotly_chart(fig_eq, use_container_width=True)

    # -----------------------------
    # DRAWDOWN
    # -----------------------------
    st.subheader("📉 Drawdown")

    fig_dd = go.Figure()
    fig_dd.add_trace(go.Scatter(
        x=drawdown.index,
        y=drawdown.values * 100,
        name="Drawdown %"
    ))

    fig_dd.update_layout(
        height=280,
        yaxis_title="Drawdown (%)",
        xaxis_title="Date"
    )

    st.plotly_chart(fig_dd, use_container_width=True)

    # -----------------------------
    # SUMMARY
    # -----------------------------
    st.subheader("🧠 Portfolio Experience Summary")

    c1, c2, c3 = st.columns(3)

    with c1:
        st.metric("Max Drawdown", f"{result['max_drawdown_pct']}%")

    with c2:
        st.metric("Max Drawdown Date", fmt_date(result["max_drawdown_date"]))

    with c3:
        st.metric("Recovery Date", fmt_date(result["recovery_date"]))
