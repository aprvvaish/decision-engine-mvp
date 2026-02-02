import sqlite3
import pandas as pd
import streamlit as st

DB_FILE = "scan_results.db"
TABLE = "stock_scans"

st.set_page_config(layout="wide")
st.title("📊 AI Stock Research Dashboard")
st.caption("Ideas • Strategies • Portfolio Simulation")

# =============================
# LOAD LATEST SCAN
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
# NAVIGATION
# =============================
st.subheader("🧭 Navigation")

col1, col2 = st.columns(2)

with col1:
    if st.button("📈 Stock Research"):
        st.switch_page("pages/3_Stock_Research.py")

with col2:
    if st.button("⚖️ Strategy Comparison"):
        st.switch_page("pages/2_Strategy_Comparison.py")

st.divider()

# =============================
# TOP IDEAS
# =============================
st.subheader("🔥 Top Ideas")

top_n = st.slider("Number of ideas", 3, 15, 5)

top_df = df.copy()

top_df["idea_score"] = (
    (top_df["buy_sharpe"].clip(lower=0) / 2) * 0.4 +
    (top_df["mom_sharpe"].clip(lower=0) / 2) * 0.3
)

top_df = top_df.sort_values("idea_score", ascending=False).head(top_n)

def open_stock(ticker):
    st.session_state.selected_stock = ticker
    st.switch_page("pages/3_Stock_Research.py")

for _, row in top_df.iterrows():
    c1, c2, c3 = st.columns([2, 1, 1])

    with c1:
        if st.button(row["ticker"], key=f"idea_{row['ticker']}"):
            open_stock(row["ticker"])

    with c2:
        st.write(f"BUY Sharpe: {row['buy_sharpe']}")

    with c3:
        st.write(f"Mom Sharpe: {row['mom_sharpe']}")
