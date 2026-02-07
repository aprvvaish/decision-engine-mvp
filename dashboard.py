"""
Enhanced Stock Research Platform Dashboard
Modern design with stats, quick actions, and navigation
"""

import streamlit as st
import pandas as pd
import numpy as np
import sqlite3
import plotly.graph_objects as go
from datetime import datetime, timedelta
from plotly.subplots import make_subplots

st.set_page_config(
    page_title="Stock Research Platform",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Database connection
DB_PATH = "scan_results.db"

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: 700;
        background: linear-gradient(120deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }
    .subtitle {
        font-size: 1.2rem;
        color: #666;
        margin-bottom: 2rem;
    }
    .stat-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .action-card {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        border: 2px solid #e0e0e0;
        transition: all 0.3s;
        cursor: pointer;
    }
    .action-card:hover {
        border-color: #667eea;
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.2);
        transform: translateY(-2px);
    }
    .feature-badge {
        background: #667eea;
        color: white;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 600;
    }
    .success-badge {
        background: #48bb78;
        color: white;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.85rem;
    }
    .warning-badge {
        background: #ed8936;
        color: white;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.85rem;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown('<h1 class="main-header">📊 Stock Research Platform</h1>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">AI-Powered Portfolio Optimization for Indian Equities</p>', unsafe_allow_html=True)

# Check if database exists
@st.cache_data(ttl=60)
def check_database_status():
    """Check if database exists and has data"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check if tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        if 'scan_results' not in tables:
            conn.close()
            return {
                'exists': False,
                'has_data': False,
                'message': 'Database not initialized'
            }
        
        # Check if has data
        cursor.execute("SELECT COUNT(*) FROM scan_results")
        count = cursor.fetchone()[0]
        
        # Get stats
        cursor.execute("SELECT COUNT(DISTINCT ticker) FROM scan_results")
        num_stocks = cursor.fetchone()[0]
        
        cursor.execute("SELECT MAX(date) FROM scan_results")
        last_update = cursor.fetchone()[0]
        
        # Get signals
        cursor.execute("""
            SELECT 
                SUM(buy_signal) as buy_signals,
                SUM(momentum_signal) as momentum_signals
            FROM scan_results
            WHERE date >= date('now', '-30 days')
        """)
        buy_sig, mom_sig = cursor.fetchone()
        
        # Get portfolios count
        if 'portfolios' in tables:
            cursor.execute("SELECT COUNT(*) FROM portfolios")
            num_portfolios = cursor.fetchone()[0]
        else:
            num_portfolios = 0
        
        conn.close()
        
        return {
            'exists': True,
            'has_data': count > 0,
            'total_records': count,
            'num_stocks': num_stocks,
            'last_update': last_update,
            'buy_signals': buy_sig or 0,
            'momentum_signals': mom_sig or 0,
            'num_portfolios': num_portfolios,
            'message': 'Ready'
        }
        
    except Exception as e:
        return {
            'exists': False,
            'has_data': False,
            'message': f'Error: {str(e)}'
        }

# Get database status
db_status = check_database_status()

# Status banner
if not db_status['exists'] or not db_status['has_data']:
    st.error("⚠️ **No Data Found** - Please run `python run_scan.py` to populate the database")
    
    st.info("**Quick Start:**")
    st.code("""
# 1. Run the scanner
python run_scan.py

# 2. Refresh this page
# 3. Start using the platform!
    """, language="bash")
    
    st.stop()

# Success banner
col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    st.success(f"✅ Database loaded: **{db_status['num_stocks']} stocks**, **{db_status['total_records']:,} records**")
with col2:
    last_update = datetime.strptime(db_status['last_update'], '%Y-%m-%d')
    days_ago = (datetime.now() - last_update).days
    
    if days_ago == 0:
        update_status = "🟢 Today"
    elif days_ago == 1:
        update_status = "🟡 Yesterday"
    elif days_ago <= 7:
        update_status = f"🟡 {days_ago}d ago"
    else:
        update_status = f"🔴 {days_ago}d ago"
    
    st.info(f"Last scan: {update_status}")
with col3:
    if db_status['num_portfolios'] > 0:
        st.info(f"💼 {db_status['num_portfolios']} portfolios")
    else:
        st.warning("💼 No portfolios")

st.divider()

# Main dashboard content
col1, col2, col3, col4 = st.columns(4)

# Metric cards
with col1:
    st.metric(
        label="📈 Stocks Tracked",
        value=db_status['num_stocks'],
        delta=f"{db_status['num_stocks']} active"
    )

with col2:
    st.metric(
        label="🎯 BUY Signals",
        value=db_status['buy_signals'],
        delta="Last 30 days"
    )

with col3:
    st.metric(
        label="🚀 Momentum Signals",
        value=db_status['momentum_signals'],
        delta="Last 30 days"
    )

with col4:
    total_signals = db_status['buy_signals'] + db_status['momentum_signals']
    st.metric(
        label="⚡ Total Signals",
        value=total_signals,
        delta=f"{total_signals} opportunities"
    )

st.divider()

# Quick Actions section
st.markdown("### 🚀 Quick Actions")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("""
    <div style='padding: 1.5rem; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                border-radius: 10px; color: white; text-align: center;'>
        <h3>📊 Strategy Comparison</h3>
        <p>Compare 6 allocation strategies to maximize returns</p>
        <p style='margin-top: 1rem;'><strong>Goal:</strong> ₹20L → ₹1Cr</p>
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("🔍 Compare Strategies", use_container_width=True, type="primary"):
        st.switch_page("pages/2_Strategy_Comparison.py")

with col2:
    st.markdown("""
    <div style='padding: 1.5rem; background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); 
                border-radius: 10px; color: white; text-align: center;'>
        <h3>💼 Portfolio Manager</h3>
        <p>Create, save, and compare multiple portfolios</p>
        <p style='margin-top: 1rem;'><strong>Saved:</strong> """ + str(db_status['num_portfolios']) + """ portfolios</p>
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("💾 Manage Portfolios", use_container_width=True, type="primary"):
        st.switch_page("pages/1_Portfolio_Simulator.py")

with col3:
    st.markdown("""
    <div style='padding: 1.5rem; background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); 
                border-radius: 10px; color: white; text-align: center;'>
        <h3>🔍 Stock Research</h3>
        <p>Technical analysis with charts and indicators</p>
        <p style='margin-top: 1rem;'><strong>View:</strong> Price & signals</p>
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("📈 Research Stocks", use_container_width=True, type="primary"):
        st.switch_page("pages/3_Stock_Research.py")

st.divider()

# Recent signals section
st.markdown("### 🎯 Recent Signals (Last 30 Days)")

@st.cache_data(ttl=300)
def get_recent_signals():
    """Get stocks with recent signals"""
    conn = sqlite3.connect(DB_PATH)
    
    query = """
    WITH recent_signals AS (
        SELECT 
            ticker,
            date,
            close_price,
            buy_signal,
            momentum_signal,
            rsi,
            ROW_NUMBER() OVER (PARTITION BY ticker ORDER BY date DESC) as rn
        FROM scan_results
        WHERE date >= date('now', '-30 days')
        AND (buy_signal = 1 OR momentum_signal = 1)
    )
    SELECT 
        ticker,
        date,
        close_price,
        buy_signal,
        momentum_signal,
        rsi
    FROM recent_signals
    WHERE rn = 1
    ORDER BY date DESC, momentum_signal DESC, buy_signal DESC
    LIMIT 10
    """
    
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    return df

signals_df = get_recent_signals()

if not signals_df.empty:
    # Format the dataframe
    display_df = signals_df.copy()
    display_df['Signal'] = display_df.apply(
        lambda x: '🚀 Momentum' if x['momentum_signal'] else '🎯 BUY', axis=1
    )
    display_df['Price'] = display_df['close_price'].apply(lambda x: f"₹{x:.2f}")
    display_df['RSI'] = display_df['rsi'].apply(lambda x: f"{x:.1f}")
    
    # Display columns
    display_cols = ['ticker', 'Signal', 'date', 'Price', 'RSI']
    display_df = display_df[display_cols]
    display_df.columns = ['Stock', 'Signal', 'Date', 'Price', 'RSI']
    
    st.dataframe(
        display_df,
        hide_index=True,
        use_container_width=True,
        column_config={
            "Stock": st.column_config.TextColumn("Stock", width="medium"),
            "Signal": st.column_config.TextColumn("Signal", width="medium"),
            "Date": st.column_config.DateColumn("Date", width="small"),
            "Price": st.column_config.TextColumn("Price", width="small"),
            "RSI": st.column_config.TextColumn("RSI", width="small")
        }
    )
else:
    st.info("No recent signals. Run a fresh scan to get updated signals.")

st.divider()

# Market overview section
st.markdown("### 📊 Market Overview")

@st.cache_data(ttl=300)
def get_market_stats():
    """Get market statistics"""
    conn = sqlite3.connect(DB_PATH)
    
    # Get latest data for each stock
    query = """
    WITH latest AS (
        SELECT 
            ticker,
            close_price,
            sma_50,
            sma_200,
            rsi,
            ROW_NUMBER() OVER (PARTITION BY ticker ORDER BY date DESC) as rn
        FROM scan_results
    )
    SELECT 
        ticker,
        close_price,
        sma_50,
        sma_200,
        rsi
    FROM latest
    WHERE rn = 1
    """
    
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    if df.empty:
        return None
    
    # Calculate stats
    stats = {
        'total_stocks': len(df),
        'bullish': len(df[(df['close_price'] > df['sma_50']) & (df['sma_50'] > df['sma_200'])]),
        'bearish': len(df[(df['close_price'] < df['sma_50']) & (df['sma_50'] < df['sma_200'])]),
        'overbought': len(df[df['rsi'] > 70]),
        'oversold': len(df[df['rsi'] < 30]),
        'neutral': 0
    }
    
    stats['neutral'] = stats['total_stocks'] - stats['bullish'] - stats['bearish']
    
    return stats

market_stats = get_market_stats()

if market_stats:
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        bullish_pct = (market_stats['bullish'] / market_stats['total_stocks']) * 100
        st.metric(
            label="🟢 Bullish Trend",
            value=f"{market_stats['bullish']} stocks",
            delta=f"{bullish_pct:.1f}%"
        )
    
    with col2:
        bearish_pct = (market_stats['bearish'] / market_stats['total_stocks']) * 100
        st.metric(
            label="🔴 Bearish Trend",
            value=f"{market_stats['bearish']} stocks",
            delta=f"{bearish_pct:.1f}%"
        )
    
    with col3:
        st.metric(
            label="📈 Overbought (RSI>70)",
            value=f"{market_stats['overbought']} stocks",
            delta="Potential correction"
        )
    
    with col4:
        st.metric(
            label="📉 Oversold (RSI<30)",
            value=f"{market_stats['oversold']} stocks",
            delta="Potential bounce"
        )
    
    # Trend distribution chart
    fig = go.Figure(data=[go.Pie(
        labels=['Bullish', 'Neutral', 'Bearish'],
        values=[market_stats['bullish'], market_stats['neutral'], market_stats['bearish']],
        hole=0.4,
        marker_colors=['#48bb78', '#ecc94b', '#f56565']
    )])
    
    fig.update_layout(
        title="Market Trend Distribution",
        height=300,
        showlegend=True
    )
    
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# Platform features section
st.markdown("### ✨ Platform Features")

col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    #### 📊 Strategy Optimization
    - **6 Allocation Strategies**: Equal Weight, Risk Parity, Min Variance, Max Sharpe, Momentum, Kelly
    - **Goal-Based Planning**: ₹20L → ₹1Cr projections
    - **Risk-Return Analysis**: Sharpe ratio, volatility, drawdown
    - **Efficient Frontier**: Visual optimization
    
    #### 💼 Portfolio Management
    - **Save Unlimited Portfolios**: Never lose your configurations
    - **Compare Side-by-Side**: See allocation differences
    - **Export to CSV**: Use in Excel or Google Sheets
    - **Version Control**: Track portfolio evolution
    """)

with col2:
    st.markdown("""
    #### 🔍 Technical Analysis
    - **Price Charts**: SMA 50/200, signals marked
    - **RSI Indicator**: Momentum analysis
    - **Signal Detection**: BUY and Momentum flags
    - **Type-to-Search**: Quick stock lookup
    
    #### 🗄️ Data Management
    - **SQLite Database**: Fast, reliable storage
    - **Automatic Scanning**: Run `run_scan.py`
    - **Real-time Updates**: Latest market data
    - **30+ Indian Stocks**: Large & mid-cap coverage
    """)

st.divider()

# Quick tips
with st.expander("💡 Quick Tips", expanded=False):
    st.markdown("""
    ### Getting Started
    1. **Run Scanner** - `python run_scan.py` to get latest data
    2. **Compare Strategies** - Find best allocation method for your goals
    3. **Create Portfolio** - Build and save your portfolio
    4. **Research Stocks** - Analyze individual stocks
    
    ### Best Practices
    - 🔄 **Scan weekly** - Keep data fresh
    - 💾 **Save portfolios** - Track multiple strategies
    - 📊 **Compare often** - Learn from differences
    - 🎯 **Set goals** - ₹20L → ₹1Cr in X years
    
    ### Performance Tips
    - Use **Max Sharpe** strategy for balanced returns
    - Maintain **5-30 stocks** for diversification
    - Keep **max position <10%** to limit risk
    - **Rebalance quarterly** to maintain allocation
    
    ### Need Help?
    - 📚 Check `USER_GUIDE.md` for detailed instructions
    - 🔧 See `SCAN_TROUBLESHOOTING.md` for scanner issues
    - 💼 Read `PORTFOLIO_MANAGEMENT_GUIDE.md` for workflows
    """)

# Footer
st.divider()

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("""
    **🎯 Current Goal**  
    ₹20 Lakhs → ₹1 Crore  
    10-year timeline
    """)

with col2:
    st.markdown("""
    **📈 Required CAGR**  
    ~17.5% annually  
    Achievable with right strategy
    """)

with col3:
    st.markdown("""
    **⚠️ Disclaimer**  
    Educational purposes only  
    Not financial advice
    """)

st.markdown("---")
st.caption("Built with ❤️ for Indian equity investors | Last updated: " + 
          datetime.now().strftime('%Y-%m-%d %H:%M'))
