import sqlite3
import pandas as pd
import streamlit as st

DB_FILE = "scan_results.db"
TABLE = "stock_scans"

st.set_page_config(layout="wide")
st.title("⚖️ Strategy Comparison Dashboard")

@st.cache_data(ttl=300)
def load_latest():
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql(
        f"""
        SELECT * FROM {TABLE}
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
# SUMMARY
# =============================
summary = pd.DataFrame({
    "Strategy": ["BUY", "Momentum"],
    "Avg Sharpe": [df["buy_sharpe"].mean(), df["mom_sharpe"].mean()],
    "Avg Return %": [df["buy_return_pct"].mean(), df["mom_return_pct"].mean()],
    "Avg Max Drawdown %": [df["buy_max_dd"].mean(), df["mom_max_dd"].mean()],
})

st.subheader("📊 Strategy Summary")
st.dataframe(summary, use_container_width=True)

st.divider()

# =============================
# CLICKABLE STOCK ROWS
# =============================
st.subheader("📋 Stock-level Metrics (click to open chart)")

def open_stock(ticker):
    st.session_state.selected_stock = ticker
    st.switch_page("pages/3_Stock_Research.py")

for _, row in df.iterrows():
    c1, c2, c3, c4 = st.columns([2, 1, 1, 1])

    with c1:
        if st.button(row["ticker"], key=f"str_{row['ticker']}"):
            open_stock(row["ticker"])

    with c2:
        st.write(f"BUY Sharpe: {row['buy_sharpe']}")

    with c3:
        st.write(f"Mom Sharpe: {row['mom_sharpe']}")

    with c4:
        st.write(f"DD: {row['buy_max_dd']}%")
