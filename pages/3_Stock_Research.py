"""
Enhanced Stock Research Page
Advanced technical and fundamental analysis with comprehensive company insights
"""

import streamlit as st
import pandas as pd
import numpy as np
import sqlite3
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import sys
import os

# Import fundamental analysis module
from fundamental_analysis import FundamentalAnalyzer, format_large_number, format_percentage

st.set_page_config(page_title="Stock Research", page_icon="🔍", layout="wide")

# Custom CSS
st.markdown("""
<style>
    .stock-header {
        font-size: 2.5rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
    }
    .metric-positive {
        color: #48bb78;
        font-weight: 600;
    }
    .metric-negative {
        color: #f56565;
        font-weight: 600;
    }
    .signal-badge {
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 600;
        display: inline-block;
        margin: 0.25rem;
    }
    .buy-signal {
        background: #48bb78;
        color: white;
    }
    .momentum-signal {
        background: #667eea;
        color: white;
    }
    .info-box {
        background: #f7fafc;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #667eea;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Database connection
DB_PATH = "scan_results.db"

@st.cache_data(ttl=300)
def get_all_stocks():
    """Get list of all available stocks"""
    conn = sqlite3.connect(DB_PATH)
    query = "SELECT DISTINCT ticker FROM scan_results ORDER BY ticker"
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df['ticker'].tolist()

@st.cache_data(ttl=300)
def get_stock_data(ticker, days=365):
    """Get historical data for a stock"""
    conn = sqlite3.connect(DB_PATH)
    
    query = f"""
    SELECT 
        date,
        open_price,
        high_price,
        low_price,
        close_price,
        volume,
        sma_50,
        sma_200,
        rsi,
        macd,
        macd_signal,
        bb_upper,
        bb_lower,
        bb_middle,
        buy_signal,
        momentum_signal
    FROM scan_results
    WHERE ticker = '{ticker}'
    ORDER BY date DESC
    LIMIT {days}
    """
    
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    if not df.empty:
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')
        
        # Calculate additional metrics
        df['price_change'] = df['close_price'].diff()
        df['price_change_pct'] = df['close_price'].pct_change() * 100
        df['volume_sma'] = df['volume'].rolling(window=20).mean()
        
    return df

@st.cache_data(ttl=300)
def get_stock_stats(ticker):
    """Get summary statistics for a stock"""
    conn = sqlite3.connect(DB_PATH)
    
    query = f"""
    SELECT 
        close_price,
        sma_50,
        sma_200,
        rsi,
        volume,
        buy_signal,
        momentum_signal,
        date
    FROM scan_results
    WHERE ticker = '{ticker}'
    ORDER BY date DESC
    LIMIT 1
    """
    
    df = pd.read_sql_query(query, conn)
    
    # Get 52-week high/low
    query_52w = f"""
    SELECT 
        MAX(high_price) as week_52_high,
        MIN(low_price) as week_52_low,
        MIN(date) as start_date,
        MAX(date) as end_date
    FROM scan_results
    WHERE ticker = '{ticker}'
    AND date >= date('now', '-365 days')
    """
    
    df_52w = pd.read_sql_query(query_52w, conn)
    
    # Get recent performance
    query_perf = f"""
    WITH recent AS (
        SELECT close_price, date,
               ROW_NUMBER() OVER (ORDER BY date DESC) as rn
        FROM scan_results
        WHERE ticker = '{ticker}'
    )
    SELECT 
        MAX(CASE WHEN rn = 1 THEN close_price END) as current,
        MAX(CASE WHEN rn = 2 THEN close_price END) as prev_day,
        MAX(CASE WHEN rn = 6 THEN close_price END) as week_ago,
        MAX(CASE WHEN rn = 31 THEN close_price END) as month_ago
    FROM recent
    WHERE rn <= 31
    """
    
    df_perf = pd.read_sql_query(query_perf, conn)
    
    # Get signal counts
    query_signals = f"""
    SELECT 
        SUM(buy_signal) as total_buy_signals,
        SUM(momentum_signal) as total_momentum_signals
    FROM scan_results
    WHERE ticker = '{ticker}'
    AND date >= date('now', '-90 days')
    """
    
    df_signals = pd.read_sql_query(query_signals, conn)
    
    conn.close()
    
    # Combine all stats
    stats = df.iloc[0].to_dict() if not df.empty else {}
    stats.update(df_52w.iloc[0].to_dict() if not df_52w.empty else {})
    stats.update(df_perf.iloc[0].to_dict() if not df_perf.empty else {})
    stats.update(df_signals.iloc[0].to_dict() if not df_signals.empty else {})
    
    return stats

def create_price_chart(df, ticker, chart_type='candlestick'):
    """Create interactive price chart with indicators"""
    
    # Create subplots
    fig = make_subplots(
        rows=4, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.5, 0.15, 0.15, 0.2],
        subplot_titles=(f'{ticker} - Price & Indicators', 'RSI', 'MACD', 'Volume')
    )
    
    # Price chart
    if chart_type == 'candlestick':
        fig.add_trace(
            go.Candlestick(
                x=df['date'],
                open=df['open_price'],
                high=df['high_price'],
                low=df['low_price'],
                close=df['close_price'],
                name='Price',
                increasing_line_color='#48bb78',
                decreasing_line_color='#f56565'
            ),
            row=1, col=1
        )
    else:  # Line chart
        fig.add_trace(
            go.Scatter(
                x=df['date'],
                y=df['close_price'],
                name='Close Price',
                line=dict(color='#667eea', width=2)
            ),
            row=1, col=1
        )
    
    # SMA 50
    fig.add_trace(
        go.Scatter(
            x=df['date'],
            y=df['sma_50'],
            name='SMA 50',
            line=dict(color='orange', width=1.5, dash='dash')
        ),
        row=1, col=1
    )
    
    # SMA 200
    fig.add_trace(
        go.Scatter(
            x=df['date'],
            y=df['sma_200'],
            name='SMA 200',
            line=dict(color='red', width=1.5, dash='dash')
        ),
        row=1, col=1
    )
    
    # Bollinger Bands
    fig.add_trace(
        go.Scatter(
            x=df['date'],
            y=df['bb_upper'],
            name='BB Upper',
            line=dict(color='gray', width=1, dash='dot'),
            opacity=0.5
        ),
        row=1, col=1
    )
    
    fig.add_trace(
        go.Scatter(
            x=df['date'],
            y=df['bb_lower'],
            name='BB Lower',
            line=dict(color='gray', width=1, dash='dot'),
            fill='tonexty',
            opacity=0.3
        ),
        row=1, col=1
    )
    
    # BUY signals
    buy_signals = df[df['buy_signal'] == 1]
    if not buy_signals.empty:
        fig.add_trace(
            go.Scatter(
                x=buy_signals['date'],
                y=buy_signals['close_price'],
                mode='markers',
                name='BUY Signal',
                marker=dict(
                    symbol='triangle-up',
                    size=12,
                    color='#48bb78',
                    line=dict(color='white', width=2)
                )
            ),
            row=1, col=1
        )
    
    # Momentum signals
    momentum_signals = df[df['momentum_signal'] == 1]
    if not momentum_signals.empty:
        fig.add_trace(
            go.Scatter(
                x=momentum_signals['date'],
                y=momentum_signals['close_price'],
                mode='markers',
                name='Momentum Signal',
                marker=dict(
                    symbol='diamond',
                    size=12,
                    color='#667eea',
                    line=dict(color='white', width=2)
                )
            ),
            row=1, col=1
        )
    
    # RSI
    fig.add_trace(
        go.Scatter(
            x=df['date'],
            y=df['rsi'],
            name='RSI',
            line=dict(color='purple', width=2)
        ),
        row=2, col=1
    )
    
    # RSI overbought/oversold lines
    fig.add_hline(y=70, line_dash="dash", line_color="red", opacity=0.5, row=2, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="green", opacity=0.5, row=2, col=1)
    
    # MACD
    fig.add_trace(
        go.Scatter(
            x=df['date'],
            y=df['macd'],
            name='MACD',
            line=dict(color='blue', width=2)
        ),
        row=3, col=1
    )
    
    fig.add_trace(
        go.Scatter(
            x=df['date'],
            y=df['macd_signal'],
            name='Signal',
            line=dict(color='orange', width=2)
        ),
        row=3, col=1
    )
    
    # MACD histogram
    macd_hist = df['macd'] - df['macd_signal']
    colors = ['green' if val >= 0 else 'red' for val in macd_hist]
    
    fig.add_trace(
        go.Bar(
            x=df['date'],
            y=macd_hist,
            name='MACD Histogram',
            marker_color=colors,
            opacity=0.5
        ),
        row=3, col=1
    )
    
    # Volume
    colors_vol = ['green' if row['close_price'] >= row['open_price'] else 'red' 
                  for _, row in df.iterrows()]
    
    fig.add_trace(
        go.Bar(
            x=df['date'],
            y=df['volume'],
            name='Volume',
            marker_color=colors_vol,
            opacity=0.5
        ),
        row=4, col=1
    )
    
    # Volume SMA
    if 'volume_sma' in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df['date'],
                y=df['volume_sma'],
                name='Vol SMA',
                line=dict(color='orange', width=2)
            ),
            row=4, col=1
        )
    
    # Update layout
    fig.update_layout(
        height=1000,
        showlegend=True,
        hovermode='x unified',
        xaxis_rangeslider_visible=False
    )
    
    fig.update_yaxes(title_text="Price (₹)", row=1, col=1)
    fig.update_yaxes(title_text="RSI", row=2, col=1, range=[0, 100])
    fig.update_yaxes(title_text="MACD", row=3, col=1)
    fig.update_yaxes(title_text="Volume", row=4, col=1)
    
    return fig

def get_stock_recommendation(stats):
    """Generate stock recommendation based on indicators"""
    if not stats:
        return "Insufficient data", "gray"
    
    score = 0
    signals = []
    
    # Trend analysis
    if stats.get('close_price', 0) > stats.get('sma_50', 0) > stats.get('sma_200', 0):
        score += 3
        signals.append("✅ Strong uptrend (Price > SMA50 > SMA200)")
    elif stats.get('close_price', 0) > stats.get('sma_50', 0):
        score += 1
        signals.append("🟡 Uptrend (Price > SMA50)")
    elif stats.get('close_price', 0) < stats.get('sma_50', 0) < stats.get('sma_200', 0):
        score -= 3
        signals.append("❌ Strong downtrend")
    else:
        score -= 1
        signals.append("🟡 Downtrend")
    
    # RSI analysis
    rsi = stats.get('rsi', 50)
    if 30 < rsi < 70:
        score += 1
        signals.append(f"✅ RSI neutral ({rsi:.1f})")
    elif rsi < 30:
        score += 2
        signals.append(f"🟢 RSI oversold ({rsi:.1f}) - potential bounce")
    elif rsi > 70:
        score -= 2
        signals.append(f"🔴 RSI overbought ({rsi:.1f}) - potential correction")
    
    # Recent signals
    if stats.get('buy_signal'):
        score += 2
        signals.append("🎯 Recent BUY signal")
    
    if stats.get('momentum_signal'):
        score += 2
        signals.append("🚀 Recent Momentum signal")
    
    # Generate recommendation
    if score >= 5:
        recommendation = "Strong Buy"
        color = "#48bb78"
    elif score >= 2:
        recommendation = "Buy"
        color = "#68d391"
    elif score >= -1:
        recommendation = "Hold"
        color = "#ecc94b"
    elif score >= -4:
        recommendation = "Sell"
        color = "#fc8181"
    else:
        recommendation = "Strong Sell"
        color = "#f56565"
    
    return recommendation, color, signals, score

# Header
st.title("🔍 Stock Research & Analysis")
st.markdown("**Comprehensive Technical & Fundamental Analysis**")

# Check database
available_stocks = get_all_stocks()

if not available_stocks:
    st.error("⚠️ No stock data found. Please run `python run_scan.py` first.")
    st.stop()

st.success(f"✅ {len(available_stocks)} stocks available for research")

st.divider()

# Global stock selector (applies to all tabs)
col1, col2, col3 = st.columns([3, 1, 1])

with col1:
    selected_stock = st.selectbox(
        "🎯 Select Stock (applies to all tabs)",
        options=available_stocks,
        index=0,
        key="global_stock_selector",
        help="This stock selection applies across all analysis tabs"
    )

with col2:
    if st.button("🔄 Refresh Data", key="global_refresh", use_container_width=True):
        st.rerun()

with col3:
    st.metric("Selected", selected_stock.replace('.NS', ''))

st.divider()

# Main layout with more tabs
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10 = st.tabs([
    "📊 Technical Analysis", 
    "💼 Fundamentals",
    "📈 Financials & Results",
    "⚖️ Valuation & Peers",
    "💰 Cash Flow Analysis",
    "👔 Management Quality",
    "🔮 Future Outlook",
    "⚠️ Risks & Warnings",
    "🔍 Compare Stocks",
    "📋 Watchlist"
])

# ============================================================================
# TAB 1: TECHNICAL ANALYSIS
# ============================================================================

with tab1:
    # Chart display options (stock already selected globally)
    col1, col2 = st.columns(2)
    
    with col1:
        chart_type = st.selectbox(
            "Chart Type",
            options=['Candlestick', 'Line'],
            index=0,
            key="tab1_chart_type"
        )
    
    with col2:
        days_to_show = st.selectbox(
            "Time Period",
            options=[30, 90, 180, 365],
            format_func=lambda x: f"{x} days" if x < 365 else "1 year",
            index=3,
            key="tab1_days"
        )
    
    # Load data for the globally selected stock
    df = get_stock_data(selected_stock, days_to_show)
    stats = get_stock_stats(selected_stock)
    
    if df.empty:
        st.error(f"No data available for {selected_stock}")
    else:
            # Stock header
            latest = df.iloc[-1]
            prev = df.iloc[-2] if len(df) > 1 else df.iloc[-1]
            
            col1, col2, col3, col4, col5 = st.columns(5)
            
            with col1:
                price_change = latest['close_price'] - prev['close_price']
                price_change_pct = (price_change / prev['close_price']) * 100
                
                st.metric(
                    "Current Price",
                    f"₹{latest['close_price']:.2f}",
                    f"{price_change:+.2f} ({price_change_pct:+.2f}%)"
                )
            
            with col2:
                st.metric(
                    "52W High",
                    f"₹{stats.get('week_52_high', 0):.2f}"
                )
            
            with col3:
                st.metric(
                    "52W Low",
                    f"₹{stats.get('week_52_low', 0):.2f}"
                )
            
            with col4:
                st.metric(
                    "RSI",
                    f"{latest['rsi']:.1f}",
                    "Overbought" if latest['rsi'] > 70 else "Oversold" if latest['rsi'] < 30 else "Neutral"
                )
            
            with col5:
                st.metric(
                    "Volume",
                    f"{latest['volume']:,.0f}"
                )
            
            st.divider()
            
            # Performance metrics
            st.subheader("📈 Performance")
            
            col1, col2, col3 = st.columns(3)
            
            current_price = stats.get('current', 0)
            
            with col1:
                day_change = ((current_price - stats.get('prev_day', current_price)) / stats.get('prev_day', current_price)) * 100
                st.metric("1 Day", f"{day_change:+.2f}%")
            
            with col2:
                week_change = ((current_price - stats.get('week_ago', current_price)) / stats.get('week_ago', current_price)) * 100
                st.metric("1 Week", f"{week_change:+.2f}%")
            
            with col3:
                month_change = ((current_price - stats.get('month_ago', current_price)) / stats.get('month_ago', current_price)) * 100
                st.metric("1 Month", f"{month_change:+.2f}%")
            
            st.divider()
            
            # AI Recommendation
            recommendation, color, signals, score = get_stock_recommendation(stats)
            
            st.subheader("🤖 AI Analysis")
            
            col1, col2 = st.columns([1, 2])
            
            with col1:
                st.markdown(f"""
                <div style='text-align: center; padding: 2rem; background: {color}; 
                            color: white; border-radius: 10px; font-size: 2rem; font-weight: bold;'>
                    {recommendation}
                </div>
                <div style='text-align: center; margin-top: 0.5rem; color: gray;'>
                    Score: {score}/10
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                st.markdown("**Analysis Factors:**")
                for signal in signals:
                    st.markdown(f"- {signal}")
                
                # Signal badges
                if stats.get('total_buy_signals', 0) > 0:
                    st.markdown(f'<span class="signal-badge buy-signal">🎯 {stats["total_buy_signals"]} BUY signals (90 days)</span>', unsafe_allow_html=True)
                
                if stats.get('total_momentum_signals', 0) > 0:
                    st.markdown(f'<span class="signal-badge momentum-signal">🚀 {stats["total_momentum_signals"]} Momentum signals (90 days)</span>', unsafe_allow_html=True)
            
            st.divider()
            
            # Charts
            st.subheader("📊 Technical Charts")
            
            chart = create_price_chart(df, selected_stock, chart_type.lower())
            st.plotly_chart(chart, use_container_width=True)
            
            st.divider()
            
            # Technical indicators summary
            st.subheader("📋 Technical Indicators")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**Moving Averages:**")
                st.write(f"- SMA 50: ₹{latest['sma_50']:.2f}")
                st.write(f"- SMA 200: ₹{latest['sma_200']:.2f}")
                
                if latest['close_price'] > latest['sma_50']:
                    st.success("✅ Price above SMA 50 (Bullish)")
                else:
                    st.error("❌ Price below SMA 50 (Bearish)")
                
                if latest['sma_50'] > latest['sma_200']:
                    st.success("✅ Golden Cross formation (Bullish)")
                else:
                    st.warning("⚠️ Death Cross formation (Bearish)")
            
            with col2:
                st.markdown("**Bollinger Bands:**")
                st.write(f"- Upper: ₹{latest['bb_upper']:.2f}")
                st.write(f"- Middle: ₹{latest['bb_middle']:.2f}")
                st.write(f"- Lower: ₹{latest['bb_lower']:.2f}")
                
                bb_position = (latest['close_price'] - latest['bb_lower']) / (latest['bb_upper'] - latest['bb_lower'])
                
                if bb_position > 0.8:
                    st.warning("⚠️ Near upper band (Overbought)")
                elif bb_position < 0.2:
                    st.info("💡 Near lower band (Oversold)")
                else:
                    st.success("✅ Middle of band (Neutral)")
            
            # Export option
            st.divider()
            
            csv = df.to_csv(index=False)
            st.download_button(
                label="📥 Export Data to CSV",
                data=csv,
                file_name=f"{selected_stock}_data.csv",
                mime="text/csv"
            )

# ============================================================================
# TAB 2: FUNDAMENTALS
# ============================================================================

with tab2:
    st.subheader("💼 Company Fundamentals")
    
    st.info("💡 **Note:** This feature requires internet connection. Tickers are automatically formatted for Yahoo Finance (e.g., SBIN → SBIN.NS)")
    
    # Use globally selected stock
    try:
        with st.spinner(f"Fetching fundamental data for {selected_stock}..."):
            analyzer = FundamentalAnalyzer(selected_stock)
            company_info = analyzer.get_company_info()
        
        if company_info['name'] == 'N/A':
            st.warning(f"""
⚠️ **No fundamental data available for {selected_stock}**

**Possible reasons:**
1. Stock ticker may not be recognized by Yahoo Finance
2. Limited data for small-cap stocks
3. Internet connection issue

**Try:**
- Select a different stock (Nifty 50 stocks work best)
- Check internet connection
- Run test: `python test_fundamental_analysis.py`
            """)
            st.stop()
        
        st.divider()
        
        # Company Overview
        st.markdown("### 🏢 Company Overview")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Company", company_info['name'])
            st.caption(f"**Sector:** {company_info['sector']}")
            st.caption(f"**Industry:** {company_info['industry']}")
        
        with col2:
            st.metric("Market Cap", format_large_number(company_info['market_cap']))
            st.caption(f"**Location:** {company_info['city']}, {company_info['country']}")
            if company_info['employees'] != 'N/A':
                st.caption(f"**Employees:** {company_info['employees']:,}")
        
        with col3:
            if company_info['website'] != 'N/A':
                st.markdown(f"**Website:** [{company_info['website']}]({company_info['website']})")
        
        # Company Description
        if company_info['description'] != 'N/A':
            with st.expander("📄 About the Company", expanded=False):
                st.write(company_info['description'])
        
        st.divider()
        
        # Fundamental Score
        st.markdown("### 📊 Fundamental Score")
        
        fund_score = analyzer.generate_fundamental_score()
        
        if fund_score['score'] == 0 and fund_score['rating'] == 'Unavailable':
            st.info("⚠️ Fundamental scoring requires complete financial data which may not be available for this stock")
        else:
            col1, col2, col3 = st.columns([2, 1, 1])
            
            with col1:
                # Score gauge
                score_pct = (fund_score['score'] / fund_score['max_score']) * 100
                
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, {fund_score['color']}22 0%, {fund_score['color']}44 100%); 
                            padding: 20px; border-radius: 10px; border-left: 4px solid {fund_score['color']};">
                    <h2 style="color: {fund_score['color']}; margin: 0;">{fund_score['rating']}</h2>
                    <p style="font-size: 2rem; font-weight: bold; margin: 10px 0;">
                        {fund_score['score']}/{fund_score['max_score']}
                    </p>
                    <div style="background: #e0e0e0; border-radius: 10px; height: 20px; overflow: hidden;">
                        <div style="background: {fund_score['color']}; width: {score_pct}%; height: 100%;"></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                st.metric("Valuation", f"{fund_score['breakdown'].get('valuation', 0)}/30")
                st.caption("P/E, P/B ratios")
            
            with col3:
                st.metric("Profitability", f"{fund_score['breakdown'].get('profitability', 0)}/40")
                st.caption("Margins, ROE, Growth")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric("Financial Health", f"{fund_score['breakdown'].get('health', 0)}/30")
                st.caption("Liquidity, Debt, Cash Flow")
            
            st.info("**Score Interpretation:** Excellent (80+) | Good (60-80) | Average (40-60) | Below Average (20-40) | Poor (<20)")
        
    except Exception as e:
        st.error(f"""
❌ **Error loading fundamental data**

**Error details:** {str(e)}

**Troubleshooting:**
1. Check internet connection
2. Run test script: `python test_fundamental_analysis.py`
3. Try a different stock (Nifty 50 stocks work best)
4. Ensure yfinance is installed: `pip install yfinance`

**Note:** Some stocks may have limited fundamental data available.
        """)
        
        with st.expander("🔧 Debug Information"):
            import traceback
            st.code(traceback.format_exc())

# ============================================================================
# ============================================================================
# TAB 3: FINANCIALS & RESULTS
# ============================================================================

with tab3:
    st.subheader("📈 Financial Results & Revenue Trends")
    
    st.info("💡 **Note:** Quarterly results require internet connection. Data availability varies by stock.")
    
    # Use globally selected stock
    try:
        with st.spinner(f"Fetching financial data for {selected_stock}..."):
            analyzer = FundamentalAnalyzer(selected_stock)
        
        st.divider()
        
        # Revenue Trends
        st.markdown("### 💰 Revenue Growth Trends")
        
        revenue_data = analyzer.get_revenue_trends()
        
        if revenue_data.get('status') == 'available':
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric(
                    "Latest Revenue",
                    format_large_number(revenue_data['latest_revenue']),
                    delta=None
                )
            
            with col2:
                qoq = revenue_data.get('qoq_growth', 0)
                st.metric(
                    "QoQ Growth",
                    f"{qoq:+.2f}%",
                    delta=f"{qoq:+.2f}%"
                )
            
            with col3:
                if revenue_data.get('yoy_growth') is not None:
                    yoy = revenue_data['yoy_growth']
                    st.metric(
                        "YoY Growth",
                        f"{yoy:+.2f}%",
                        delta=f"{yoy:+.2f}%"
                    )
                else:
                    st.metric("YoY Growth", "N/A")
            
            # Revenue trend chart
            if revenue_data.get('revenue_trend'):
                fig_rev = go.Figure()
                
                fig_rev.add_trace(go.Bar(
                    x=list(range(len(revenue_data['revenue_trend']))),
                    y=revenue_data['revenue_trend'],
                    marker_color='#667eea',
                    name='Revenue'
                ))
                
                fig_rev.update_layout(
                    title="Quarterly Revenue Trend (Latest to Oldest)",
                    xaxis_title="Quarter",
                    yaxis_title="Revenue (₹)",
                    height=400
                )
                
                st.plotly_chart(fig_rev, use_container_width=True)
        else:
            st.warning(f"""
⚠️ **Revenue data not available for {selected_stock}**

Quarterly financial data may not be available for:
- Small-cap stocks
- Recently listed companies
- Stocks with limited Yahoo Finance coverage

**Try:** Select a Nifty 50 stock (RELIANCE.NS, TCS.NS, INFY.NS, etc.)
            """)
        
        st.divider()
        
        # Profitability Metrics
        st.markdown("### 📊 Profitability Metrics")
        
        profitability = analyzer.get_profitability_metrics()
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            profit_margin = profitability.get('profit_margin')
            if profit_margin is not None:
                st.metric("Profit Margin", format_percentage(profit_margin))
            else:
                st.metric("Profit Margin", "N/A")
        
        with col2:
            roe = profitability.get('roe')
            if roe is not None:
                st.metric("ROE", format_percentage(roe))
            else:
                st.metric("ROE", "N/A")
        
        with col3:
            revenue_growth = profitability.get('revenue_growth')
            if revenue_growth is not None:
                st.metric("Revenue Growth", format_percentage(revenue_growth))
            else:
                st.metric("Revenue Growth", "N/A")
        
        with col4:
            earnings_growth = profitability.get('earnings_growth')
            if earnings_growth is not None:
                st.metric("Earnings Growth", format_percentage(earnings_growth))
            else:
                st.metric("Earnings Growth", "N/A")
        
        st.divider()
        
        # Quarterly Results Table
        st.markdown("### 📅 Quarterly Results (Last 8 Quarters)")
        
        quarterly = analyzer.get_quarterly_results()
        
        if not quarterly.empty:
            # Display selected key metrics
            display_cols = []
            
            if 'Total Revenue' in quarterly.columns:
                display_cols.append('Total Revenue')
            if 'Gross Profit' in quarterly.columns:
                display_cols.append('Gross Profit')
            if 'Operating Income' in quarterly.columns:
                display_cols.append('Operating Income')
            if 'Net Income' in quarterly.columns:
                display_cols.append('Net Income')
            
            if display_cols:
                quarterly_display = quarterly[display_cols].copy()
                
                # Format large numbers
                for col in display_cols:
                    quarterly_display[col] = quarterly_display[col].apply(
                        lambda x: format_large_number(x) if pd.notna(x) else 'N/A'
                    )
                
                st.dataframe(quarterly_display, use_container_width=True)
            else:
                st.info("Detailed quarterly breakdown not available - showing available fields")
                st.dataframe(quarterly.head(), use_container_width=True)
        else:
            st.info(f"""
📊 **Quarterly results table not available for {selected_stock}**

Some stocks may have limited historical financial data.

**Available data:**
- Profitability metrics (shown above)
- Valuation ratios (see Valuation tab)
            """)
    
    except Exception as e:
        st.error(f"""
❌ **Error loading financial data**

**Error:** {str(e)}

**Solutions:**
1. Check internet connection
2. Try: `python test_fundamental_analysis.py`
3. Select a Nifty 50 stock
        """)
        
        with st.expander("🔧 Debug Info"):
            import traceback
            st.code(traceback.format_exc())

# ============================================================================
# TAB 4: VALUATION & PEERS
# ============================================================================

with tab4:
    st.subheader("⚖️ Valuation & Competitive Analysis")
    
    # Use globally selected stock
    try:
        with st.spinner(f"Fetching valuation data for {selected_stock}..."):
            analyzer = FundamentalAnalyzer(selected_stock)
        
        st.divider()
        
        # Valuation Metrics
        st.markdown("### 💎 Valuation Metrics")
        
        valuation = analyzer.get_valuation_metrics()
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            pe = valuation.get('pe_ratio')
            if pe:
                st.metric("P/E Ratio", f"{pe:.2f}")
                if pe < 15:
                    st.caption("🟢 Undervalued")
                elif pe > 30:
                    st.caption("🔴 Expensive")
                else:
                    st.caption("🟡 Fair")
            else:
                st.metric("P/E Ratio", "N/A")
        
        with col2:
            pb = valuation.get('pb_ratio')
            if pb:
                st.metric("P/B Ratio", f"{pb:.2f}")
                if pb < 2:
                    st.caption("🟢 Good value")
                elif pb > 5:
                    st.caption("🔴 Premium")
                else:
                    st.caption("🟡 Average")
            else:
                st.metric("P/B Ratio", "N/A")
        
        with col3:
            ps = valuation.get('ps_ratio')
            if ps:
                st.metric("P/S Ratio", f"{ps:.2f}")
            else:
                st.metric("P/S Ratio", "N/A")
        
        with col4:
            peg = valuation.get('peg_ratio')
            if peg:
                st.metric("PEG Ratio", f"{peg:.2f}")
                if peg < 1:
                    st.caption("🟢 Growth at good price")
                elif peg > 2:
                    st.caption("🔴 Expensive for growth")
                else:
                    st.caption("🟡 Fair")
            else:
                st.metric("PEG Ratio", "N/A")
        
        st.divider()
        
        # Industry Comparison
        st.markdown("### 🏭 Industry Peer Comparison")
        
        peers = analyzer.get_industry_peers()
        
        if peers:
            st.info(f"**Comparing with:** {', '.join([p.replace('.NS', '') for p in peers])}")
            
            comparison_df = analyzer.compare_with_peers(peers)
            
            if not comparison_df.empty:
                # Highlight current stock (use analyzer.ticker which has .NS)
                def highlight_current(row):
                    return ['background-color: #e3f2fd' if row['Ticker'] == analyzer.ticker else '' for _ in row]
                
                styled_df = comparison_df.style.apply(highlight_current, axis=1)
                
                st.dataframe(styled_df, hide_index=True, use_container_width=True)
                
                # Analysis - use analyzer.ticker (with .NS) for comparison
                if len(comparison_df) > 1:
                    try:
                        # Filter for current stock
                        current_row = comparison_df[comparison_df['Ticker'] == analyzer.ticker]
                        
                        if not current_row.empty:
                            current_pe = current_row['P/E'].iloc[0]
                            
                            # Calculate average of peers (excluding current stock)
                            peer_rows = comparison_df[comparison_df['Ticker'] != analyzer.ticker]
                            avg_pe = peer_rows['P/E'].mean()
                            
                            if pd.notna(current_pe) and pd.notna(avg_pe):
                                if current_pe < avg_pe * 0.9:
                                    st.success(f"💡 **{selected_stock}** is trading at a discount to peers (P/E: {current_pe:.2f} vs Industry avg: {avg_pe:.2f})")
                                elif current_pe > avg_pe * 1.1:
                                    st.warning(f"⚠️ **{selected_stock}** is trading at a premium to peers (P/E: {current_pe:.2f} vs Industry avg: {avg_pe:.2f})")
                                else:
                                    st.info(f"📊 **{selected_stock}** is fairly valued relative to peers (P/E: {current_pe:.2f} vs Industry avg: {avg_pe:.2f})")
                            else:
                                st.info("P/E data not available for comparison")
                        else:
                            st.info("Current stock not found in comparison - may not have valuation data")
                    except Exception as e:
                        st.info("Unable to compare valuations - some data may be missing")
                        print(f"Comparison error: {e}")
            else:
                st.info("Peer comparison data not available")
        else:
            st.info("Industry peers not identified for this stock")
        
        st.divider()
        
        # Financial Health
        st.markdown("### 💪 Financial Health")
        
        health = analyzer.get_financial_health()
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            current_ratio = health.get('current_ratio')
            if current_ratio:
                st.metric("Current Ratio", f"{current_ratio:.2f}")
                if current_ratio > 2:
                    st.caption("🟢 Strong liquidity")
                elif current_ratio > 1:
                    st.caption("🟡 Adequate liquidity")
                else:
                    st.caption("🔴 Liquidity concern")
            else:
                st.metric("Current Ratio", "N/A")
        
        with col2:
            debt_to_equity = health.get('debt_to_equity')
            if debt_to_equity is not None:
                st.metric("Debt/Equity", f"{debt_to_equity:.2f}")
                if debt_to_equity < 0.5:
                    st.caption("🟢 Low debt")
                elif debt_to_equity < 1.5:
                    st.caption("🟡 Moderate debt")
                else:
                    st.caption("🔴 High debt")
            else:
                st.metric("Debt/Equity", "N/A")
        
        with col3:
            fcf = health.get('free_cash_flow')
            if fcf:
                st.metric("Free Cash Flow", format_large_number(fcf))
                if fcf > 0:
                    st.caption("🟢 Positive FCF")
                else:
                    st.caption("🔴 Negative FCF")
            else:
                st.metric("Free Cash Flow", "N/A")
    
    except Exception as e:
        st.error(f"""
❌ **Error loading valuation data**

**Error:** {str(e)}

**Common causes:**
1. Stock ticker format issue
2. Yahoo Finance data unavailable
3. Network connectivity problem

**Solutions:**
1. Try a different stock (RELIANCE, TCS, INFY)
2. Check internet connection
3. Run: `python test_fundamental_analysis.py`
        """)
        
        with st.expander("🔧 Debug Information"):
            import traceback
            st.code(traceback.format_exc())

# ============================================================================
# TAB 5: CASH FLOW ANALYSIS
# ============================================================================

with tab5:
    st.subheader("💰 Cash Flow Analysis")
    
    st.info("💡 **Cash flow is king!** Strong cash flows indicate a healthy, sustainable business.")
    
    # Use globally selected stock
    try:
        with st.spinner(f"Fetching cash flow data for {selected_stock}..."):
            analyzer = FundamentalAnalyzer(selected_stock)
        
        st.divider()
        
        # Cash Flow Metrics
        st.markdown("### 💵 Cash Flow Metrics")
        
        cf_analysis = analyzer.get_cash_flow_analysis()
        
        if cf_analysis.get('status') == 'available':
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                ocf = cf_analysis.get('operating_cash_flow')
                if ocf:
                    st.metric("Operating Cash Flow", format_large_number(ocf))
                    if ocf > 0:
                        st.caption("🟢 Positive OCF")
                    else:
                        st.caption("🔴 Negative OCF")
                else:
                    st.metric("Operating Cash Flow", "N/A")
            
            with col2:
                fcf = cf_analysis.get('free_cash_flow')
                if fcf:
                    st.metric("Free Cash Flow", format_large_number(fcf))
                    if fcf > 0:
                        st.caption("🟢 Cash generating")
                    else:
                        st.caption("🔴 Cash burning")
                else:
                    st.metric("Free Cash Flow", "N/A")
            
            with col3:
                capex = cf_analysis.get('capital_expenditure')
                if capex:
                    st.metric("Capital Expenditure", format_large_number(capex))
                    st.caption("Investment in assets")
                else:
                    st.metric("CapEx", "N/A")
            
            with col4:
                fcf_margin = cf_analysis.get('fcf_margin')
                if fcf_margin is not None:
                    st.metric("FCF Margin", f"{fcf_margin:.2f}%")
                    if fcf_margin > 15:
                        st.caption("🟢 Excellent")
                    elif fcf_margin > 5:
                        st.caption("🟡 Good")
                    else:
                        st.caption("🔴 Low")
                else:
                    st.metric("FCF Margin", "N/A")
            
            st.divider()
            
            # Cash Flow Quality
            st.markdown("### 📊 Cash Flow Quality")
            
            col1, col2 = st.columns(2)
            
            with col1:
                cash_to_debt = cf_analysis.get('cash_to_debt')
                if cash_to_debt is not None:
                    st.metric("Cash-to-Debt Ratio", f"{cash_to_debt:.2f}")
                    if cash_to_debt > 1.0:
                        st.success("💪 **Strong liquidity** - Cash exceeds debt")
                    elif cash_to_debt > 0.5:
                        st.info("✅ **Adequate liquidity** - Healthy cash position")
                    else:
                        st.warning("⚠️ **Monitor closely** - Debt exceeds cash")
                else:
                    st.metric("Cash-to-Debt Ratio", "N/A")
            
            with col2:
                # FCF vs Net Income comparison
                health = analyzer.get_financial_health()
                profitability = analyzer.get_profitability_metrics()
                
                if fcf and profitability.get('profit_margin'):
                    st.markdown("**Cash Quality Indicators:**")
                    st.write(f"✅ Free Cash Flow: {format_large_number(fcf)}")
                    st.write(f"✅ FCF Margin: {fcf_margin:.2f}%" if fcf_margin else "N/A")
                    
                    if fcf > 0:
                        st.success("Company generates positive cash from operations")
                    else:
                        st.warning("Company is cash flow negative - burning cash")
        else:
            st.warning(f"""
⚠️ **Cash flow data not available for {selected_stock}**

**Try:** Select a Nifty 50 stock (RELIANCE.NS, TCS.NS, INFY.NS)
            """)
        
        st.divider()
        
        # Cash Flow Insights
        with st.expander("💡 Understanding Cash Flow Metrics"):
            st.markdown("""
**Operating Cash Flow (OCF):**
- Cash generated from core business operations
- Should be positive and growing
- More reliable than net income

**Free Cash Flow (FCF):**
- OCF minus capital expenditures
- Cash available for dividends, buybacks, debt reduction
- **Most important metric** for valuation

**FCF Margin:**
- FCF as % of revenue
- >15%: Excellent cash generation
- 5-15%: Good
- <5%: Weak cash generation

**Cash-to-Debt Ratio:**
- >1.0: Strong - can pay off all debt with cash
- 0.5-1.0: Healthy position
- <0.5: Monitor debt levels

**Why Cash Flow Matters:**
- Companies can manipulate earnings, but cash is real
- Positive FCF = sustainable business
- Negative FCF = may need financing
- Growing FCF = increasing shareholder value
            """)
    
    except Exception as e:
        st.error(f"""
❌ **Error loading cash flow data**

**Error:** {str(e)}

**Solutions:**
1. Check internet connection
2. Try a different stock (Nifty 50 recommended)
3. Run: `python test_fundamental_analysis.py`
        """)
        
        with st.expander("🔧 Debug Info"):
            import traceback
            st.code(traceback.format_exc())

# ============================================================================
# TAB 6: MANAGEMENT QUALITY
# ============================================================================

with tab6:
    st.subheader("👔 Management Quality & Effectiveness")
    
    st.info("💡 **Great management creates shareholder value.** Assess how well the team is running the business.")
    
    # Use globally selected stock
    try:
        with st.spinner(f"Analyzing management quality for {selected_stock}..."):
            analyzer = FundamentalAnalyzer(selected_stock)
        
        st.divider()
        
        # Management Quality Score
        st.markdown("### 📊 Management Quality Score")
        
        mgmt_quality = analyzer.get_management_quality()
        
        if mgmt_quality.get('status') == 'available':
            col1, col2 = st.columns([2, 1])
            
            with col1:
                score = mgmt_quality.get('management_score', 0)
                
                if score >= 80:
                    rating = "Excellent"
                    color = "#48bb78"
                elif score >= 60:
                    rating = "Good"
                    color = "#667eea"
                elif score >= 40:
                    rating = "Average"
                    color = "#ed8936"
                else:
                    rating = "Below Average"
                    color = "#f56565"
                
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, {color}22 0%, {color}44 100%); 
                            padding: 20px; border-radius: 10px; border-left: 4px solid {color};">
                    <h2 style="color: {color}; margin: 0;">Management Quality: {rating}</h2>
                    <p style="font-size: 2rem; font-weight: bold; margin: 10px 0;">
                        {score}/100
                    </p>
                    <div style="background: #e0e0e0; border-radius: 10px; height: 20px; overflow: hidden;">
                        <div style="background: {color}; width: {score}%; height: 100%;"></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                st.markdown("**Score Based On:**")
                st.write("✅ Return on Equity")
                st.write("✅ Profit Margins")
                st.write("✅ Operational Efficiency")
                st.write("✅ Insider Ownership")
            
            st.divider()
            
            # Key Management Metrics
            st.markdown("### 📈 Key Performance Indicators")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                roe = mgmt_quality.get('roe')
                if roe is not None:
                    st.metric("ROE", format_percentage(roe))
                    if roe > 0.20:
                        st.caption("🟢 Excellent (>20%)")
                    elif roe > 0.15:
                        st.caption("🟡 Good (>15%)")
                    else:
                        st.caption("🔴 Below average")
                else:
                    st.metric("ROE", "N/A")
            
            with col2:
                roa = mgmt_quality.get('roa')
                if roa is not None:
                    st.metric("ROA", format_percentage(roa))
                    if roa > 0.10:
                        st.caption("🟢 Efficient")
                    else:
                        st.caption("🟡 Average")
                else:
                    st.metric("ROA", "N/A")
            
            with col3:
                profit_margin = mgmt_quality.get('profit_margin')
                if profit_margin is not None:
                    st.metric("Profit Margin", format_percentage(profit_margin))
                    if profit_margin > 0.20:
                        st.caption("🟢 High margin")
                    elif profit_margin > 0.10:
                        st.caption("🟡 Good margin")
                    else:
                        st.caption("🔴 Low margin")
                else:
                    st.metric("Profit Margin", "N/A")
            
            with col4:
                operating_margin = mgmt_quality.get('operating_margin')
                if operating_margin is not None:
                    st.metric("Operating Margin", format_percentage(operating_margin))
                    if operating_margin > 0.20:
                        st.caption("🟢 Efficient ops")
                    else:
                        st.caption("🟡 Average")
                else:
                    st.metric("Operating Margin", "N/A")
            
            st.divider()
            
            # Ownership Structure
            st.markdown("### 🏢 Ownership Structure")
            
            col1, col2 = st.columns(2)
            
            with col1:
                insider = mgmt_quality.get('insider_ownership')
                if insider is not None:
                    st.metric("Insider Ownership", format_percentage(insider))
                    if insider > 0.10:
                        st.success("💪 **High insider ownership** - Management has skin in the game")
                    elif insider > 0.05:
                        st.info("✅ **Good alignment** - Insiders own meaningful stake")
                    else:
                        st.warning("⚠️ **Low insider ownership** - Limited management stake")
                else:
                    st.metric("Insider Ownership", "N/A")
            
            with col2:
                institutional = mgmt_quality.get('institutional_ownership')
                if institutional is not None:
                    st.metric("Institutional Ownership", format_percentage(institutional))
                    if institutional > 0.60:
                        st.info("📈 **High institutional interest** - Strong professional backing")
                    elif institutional > 0.30:
                        st.info("✅ **Good institutional support**")
                    else:
                        st.caption("Moderate institutional holding")
                else:
                    st.metric("Institutional Ownership", "N/A")
        
        else:
            st.warning(f"""
⚠️ **Management quality data not available for {selected_stock}**

**Try:** Select a Nifty 50 stock (RELIANCE.NS, TCS.NS, INFY.NS)
            """)
        
        st.divider()
        
        # Management Quality Insights
        with st.expander("💡 Understanding Management Quality Metrics"):
            st.markdown("""
**Return on Equity (ROE):**
- Measures how effectively management uses shareholder capital
- >20%: Excellent management
- 15-20%: Good
- <15%: Average or below

**Return on Assets (ROA):**
- Efficiency in using company assets to generate profits
- >10%: Very efficient
- 5-10%: Good
- <5%: Needs improvement

**Profit Margin:**
- Shows pricing power and cost control
- High margins = competitive advantage or strong brand
- Low margins = competitive or commodity business

**Operating Margin:**
- Profitability before interest and taxes
- Indicates operational efficiency
- Compare with industry peers

**Insider Ownership:**
- >10%: Excellent - management highly invested
- 5-10%: Good - reasonable skin in the game
- <5%: Low - limited personal stake

**Institutional Ownership:**
- Professional money managers' stake
- High ownership = confidence from smart money
- But too high (>80%) can limit liquidity

**Why It Matters:**
- Great management compounds shareholder value over time
- Poor management destroys value even in good businesses
- Look for: High ROE, healthy margins, insider ownership
            """)
    
    except Exception as e:
        st.error(f"""
❌ **Error loading management data**

**Error:** {str(e)}

**Solutions:**
1. Check internet connection
2. Try a different stock
3. Run: `python test_fundamental_analysis.py`
        """)
        
        with st.expander("🔧 Debug Info"):
            import traceback
            st.code(traceback.format_exc())

# ============================================================================
# TAB 7: FUTURE OUTLOOK
# ============================================================================

with tab7:
    st.subheader("🔮 Future Outlook & Positioning")
    
    st.info("💡 **Where is this company headed?** Analyze growth prospects, analyst targets, and market positioning.")
    
    # Use globally selected stock
    try:
        with st.spinner(f"Analyzing future outlook for {selected_stock}..."):
            analyzer = FundamentalAnalyzer(selected_stock)
        
        st.divider()
        
        # Analyst Outlook
        st.markdown("### 📊 Analyst Consensus")
        
        outlook = analyzer.get_future_outlook()
        
        if outlook.get('status') == 'available':
            col1, col2, col3 = st.columns(3)
            
            with col1:
                current = outlook.get('current_price')
                if current:
                    st.metric("Current Price", f"₹{current:.2f}")
                else:
                    st.metric("Current Price", "N/A")
            
            with col2:
                target = outlook.get('analyst_target')
                if target:
                    st.metric("Analyst Target", f"₹{target:.2f}")
                else:
                    st.metric("Analyst Target", "N/A")
            
            with col3:
                upside = outlook.get('upside_potential')
                if upside is not None:
                    st.metric(
                        "Upside Potential",
                        f"{upside:+.2f}%",
                        delta=f"{upside:+.2f}%"
                    )
                    if upside > 20:
                        st.caption("🚀 Strong upside")
                    elif upside > 0:
                        st.caption("🟢 Positive")
                    else:
                        st.caption("🔴 Limited upside")
                else:
                    st.metric("Upside Potential", "N/A")
            
            st.divider()
            
            # Growth Metrics
            st.markdown("### 📈 Growth Prospects")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                revenue_growth = outlook.get('revenue_growth')
                if revenue_growth is not None:
                    st.metric("Revenue Growth", format_percentage(revenue_growth))
                    if revenue_growth > 0.20:
                        st.caption("🚀 High growth")
                    elif revenue_growth > 0.10:
                        st.caption("🟢 Good growth")
                    elif revenue_growth > 0:
                        st.caption("🟡 Moderate growth")
                    else:
                        st.caption("🔴 Declining")
                else:
                    st.metric("Revenue Growth", "N/A")
            
            with col2:
                earnings_growth = outlook.get('earnings_growth')
                if earnings_growth is not None:
                    st.metric("Earnings Growth", format_percentage(earnings_growth))
                    if earnings_growth > 0.20:
                        st.caption("🚀 Strong growth")
                    elif earnings_growth > 0.10:
                        st.caption("🟢 Healthy")
                    else:
                        st.caption("🟡 Moderate")
                else:
                    st.metric("Earnings Growth", "N/A")
            
            with col3:
                recommendation = outlook.get('analyst_recommendation')
                if recommendation:
                    rec_display = recommendation.replace('_', ' ').title()
                    st.metric("Recommendation", rec_display)
                    
                    if 'buy' in recommendation.lower():
                        st.caption("🟢 Positive view")
                    elif 'hold' in recommendation.lower():
                        st.caption("🟡 Neutral view")
                    else:
                        st.caption("🔴 Cautious view")
                else:
                    st.metric("Recommendation", "N/A")
            
            # Number of analysts
            num_analysts = outlook.get('num_analysts')
            if num_analysts:
                st.caption(f"📊 Based on {num_analysts} analyst opinions")
            
            st.divider()
            
            # ESG Score
            st.markdown("### 🌱 ESG & Sustainability")
            
            esg = outlook.get('esg_score')
            if esg is not None:
                col1, col2 = st.columns([1, 2])
                
                with col1:
                    st.metric("ESG Score", f"{esg:.1f}/100")
                    if esg < 20:
                        st.caption("🟢 Low risk")
                    elif esg < 30:
                        st.caption("🟡 Medium risk")
                    else:
                        st.caption("🔴 High risk")
                
                with col2:
                    st.info("""
**ESG Score Interpretation:**
- <20: Leader in sustainability (Low risk)
- 20-30: Average ESG performance (Medium risk)
- >30: ESG concerns (High risk)

Lower score = Better ESG performance
                    """)
            else:
                st.info("ESG score not available for this stock")
        
        else:
            st.warning(f"""
⚠️ **Future outlook data not available for {selected_stock}**

**Try:** Select a Nifty 50 stock (RELIANCE.NS, TCS.NS, INFY.NS)
            """)
        
        st.divider()
        
        # Future Outlook Insights
        with st.expander("💡 Understanding Future Outlook Metrics"):
            st.markdown("""
**Analyst Target Price:**
- Average price target from Wall Street analysts
- Represents 12-month forward estimate
- Compare with current price for potential upside/downside

**Upside Potential:**
- (Target - Current) / Current × 100
- >20%: Significant upside expected
- 0-20%: Moderate upside
- <0%: Downside risk

**Revenue Growth:**
- Year-over-year revenue increase
- >20%: High-growth company
- 10-20%: Good growth
- <10%: Mature/slow-growth

**Earnings Growth:**
- Year-over-year earnings increase
- Should ideally exceed revenue growth (margin expansion)
- Negative = declining profitability

**Analyst Recommendation:**
- Strong Buy: Very bullish
- Buy: Positive outlook
- Hold: Neutral, fair value
- Sell: Negative outlook

**ESG Score:**
- Environmental, Social, Governance rating
- Lower score = better sustainability practices
- Important for long-term risk assessment
- Increasingly important for institutional investors

**Why It Matters:**
- Forward-looking vs backward-looking metrics
- Analyst consensus provides market sentiment
- Growth rates indicate future potential
- ESG factors affect long-term sustainability
            """)
    
    except Exception as e:
        st.error(f"""
❌ **Error loading future outlook data**

**Error:** {str(e)}

**Solutions:**
1. Check internet connection
2. Try a different stock
3. Run: `python test_fundamental_analysis.py`
        """)
        
        with st.expander("🔧 Debug Info"):
            import traceback
            st.code(traceback.format_exc())

# ============================================================================
# TAB 8: RISKS & WARNINGS
# ============================================================================

with tab8:
    st.subheader("⚠️ Risk Factors & Warnings")
    
    # Use globally selected stock
    try:
        analyzer = FundamentalAnalyzer(selected_stock)
        company_info = analyzer.get_company_info()
        
        st.divider()
        
        st.markdown(f"### 🏢 {company_info['name']}")
        st.caption(f"**Sector:** {company_info['sector']} | **Industry:** {company_info['industry']}")
        
        st.divider()
        
        # Get risk factors
        risks = analyzer.get_risk_factors()
        
        total_risks = sum(len(v) for v in risks.values())
        
        if total_risks == 0:
            st.success("✅ **No significant risks detected** - Company shows healthy financial metrics")
        else:
            st.warning(f"⚠️ **{total_risks} risk factor(s) identified** - Review before investing")
        
        # Financial Risks
        if risks['financial_risks']:
            st.markdown("### 💰 Financial Risks")
            for risk in risks['financial_risks']:
                st.error(f"🔴 {risk}")
        
        # Operational Risks
        if risks['operational_risks']:
            st.markdown("### ⚙️ Operational Risks")
            for risk in risks['operational_risks']:
                st.warning(f"🟠 {risk}")
        
        # Market Risks
        if risks['market_risks']:
            st.markdown("### 📉 Market Risks")
            for risk in risks['market_risks']:
                st.info(f"🔵 {risk}")
        
        # Regulatory Risks
        if risks['regulatory_risks']:
            st.markdown("### 📋 Regulatory & ESG Risks")
            for risk in risks['regulatory_risks']:
                st.warning(f"🟡 {risk}")
        
        st.divider()
        
        # Risk Mitigation Tips
        with st.expander("💡 Risk Mitigation Tips", expanded=False):
            st.markdown("""
**How to manage investment risks:**

1. **Diversification** - Don't put all eggs in one basket
   - Spread across sectors and industries
   - Mix of large-cap and mid-cap stocks
   
2. **Position Sizing** - Limit exposure to any single stock
   - No more than 10-15% in one stock
   - Higher risk = smaller position
   
3. **Stop Loss** - Set exit points
   - Define max acceptable loss (e.g., -10%)
   - Stick to your plan
   
4. **Regular Monitoring** - Stay updated
   - Review quarterly results
   - Track news and developments
   - Adjust portfolio as needed
   
5. **Long-term Perspective** - Don't panic sell
   - Quality companies recover from temporary setbacks
   - Focus on fundamentals, not daily price movements
            """)
        
        st.divider()
        
        # Disclaimer
        st.caption("""
**Disclaimer:** Risk analysis is based on publicly available financial data and standard metrics. 
This is not investment advice. Conduct your own due diligence or consult a financial advisor before making investment decisions.
Past performance does not guarantee future results.
        """)
    
    except Exception as e:
        st.error(f"""
❌ **Error loading risk data**

**Error:** {str(e)}

**Solutions:**
1. Check internet connection  
2. Try a different stock (RELIANCE, TCS, INFY)
3. Run test: `python test_fundamental_analysis.py`
        """)
        
        with st.expander("🔧 Debug Info"):
            import traceback
            st.code(traceback.format_exc())

# ============================================================================
# TAB 9: COMPARE STOCKS
# ============================================================================

with tab9:
    st.subheader("⚖️ Compare Multiple Stocks")
    
    selected_for_comparison = st.multiselect(
        "Select stocks to compare (2-5 recommended)",
        options=available_stocks,
        default=available_stocks[:3] if len(available_stocks) >= 3 else available_stocks
    )
    
    if len(selected_for_comparison) < 2:
        st.info("Please select at least 2 stocks to compare")
    else:
        # Comparison time period
        comp_days = st.selectbox(
            "Comparison Period",
            options=[30, 90, 180, 365],
            format_func=lambda x: f"{x} days" if x < 365 else "1 year",
            index=2,
            key="comp_days"
        )
        
        # Load data for all stocks
        comparison_data = {}
        for stock in selected_for_comparison:
            comparison_data[stock] = get_stock_data(stock, comp_days)
        
        # Price comparison chart
        st.markdown("### 📈 Price Comparison (Normalized)")
        
        fig_comp = go.Figure()
        
        for stock, df in comparison_data.items():
            if not df.empty:
                # Normalize to 100
                normalized = (df['close_price'] / df['close_price'].iloc[0]) * 100
                
                fig_comp.add_trace(go.Scatter(
                    x=df['date'],
                    y=normalized,
                    name=stock,
                    mode='lines',
                    line=dict(width=2)
                ))
        
        fig_comp.update_layout(
            title="Price Performance (Base = 100)",
            xaxis_title="Date",
            yaxis_title="Normalized Price",
            hovermode='x unified',
            height=500
        )
        
        st.plotly_chart(fig_comp, use_container_width=True)
        
        # Comparison table
        st.markdown("### 📊 Performance Metrics")
        
        comp_stats = []
        
        for stock in selected_for_comparison:
            stats = get_stock_stats(stock)
            df = comparison_data[stock]
            
            if not df.empty and stats:
                latest = df.iloc[-1]
                first = df.iloc[0]
                
                period_return = ((latest['close_price'] - first['close_price']) / first['close_price']) * 100
                
                comp_stats.append({
                    'Stock': stock,
                    'Current Price': f"₹{stats.get('current', 0):.2f}",
                    'Period Return': f"{period_return:+.2f}%",
                    'RSI': f"{latest['rsi']:.1f}",
                    '52W High': f"₹{stats.get('week_52_high', 0):.2f}",
                    '52W Low': f"₹{stats.get('week_52_low', 0):.2f}",
                    'Signals (90d)': stats.get('total_buy_signals', 0) + stats.get('total_momentum_signals', 0)
                })
        
        comp_df = pd.DataFrame(comp_stats)
        
        st.dataframe(
            comp_df,
            hide_index=True,
            use_container_width=True
        )
        
        # Best performer
        if comp_stats:
            best_stock = max(comp_stats, key=lambda x: float(x['Period Return'].replace('%', '').replace('+', '')))
            st.success(f"🏆 **Best Performer:** {best_stock['Stock']} ({best_stock['Period Return']})")

# ============================================================================
# TAB 10: WATCHLIST
# ============================================================================

with tab10:
    st.subheader("📋 Stock Watchlist")
    
    st.info("💡 **Tip:** Use this to track your favorite stocks at a glance")
    
    # Watchlist selector
    watchlist_stocks = st.multiselect(
        "Add stocks to watchlist",
        options=available_stocks,
        default=[],
        key="watchlist"
    )
    
    if not watchlist_stocks:
        st.info("Select stocks to add to your watchlist")
    else:
        # Get stats for watchlist
        watchlist_data = []
        
        for stock in watchlist_stocks:
            stats = get_stock_stats(stock)
            df = get_stock_data(stock, 30)
            
            if stats and not df.empty:
                latest = df.iloc[-1]
                prev = df.iloc[-2] if len(df) > 1 else latest
                
                day_change = ((latest['close_price'] - prev['close_price']) / prev['close_price']) * 100
                
                recommendation, color, _, score = get_stock_recommendation(stats)
                
                watchlist_data.append({
                    'Stock': stock,
                    'Price': latest['close_price'],
                    'Change': day_change,
                    'RSI': latest['rsi'],
                    'Trend': '🟢 Up' if latest['close_price'] > latest['sma_50'] > latest['sma_200'] 
                            else '🔴 Down' if latest['close_price'] < latest['sma_50'] < latest['sma_200']
                            else '🟡 Mixed',
                    'Recommendation': recommendation,
                    'Score': score,
                    'Signals': stats.get('total_buy_signals', 0) + stats.get('total_momentum_signals', 0)
                })
        
        watchlist_df = pd.DataFrame(watchlist_data)
        
        # Display watchlist
        st.dataframe(
            watchlist_df,
            column_config={
                "Stock": "Stock",
                "Price": st.column_config.NumberColumn(
                    "Price (₹)",
                    format="₹%.2f"
                ),
                "Change": st.column_config.NumberColumn(
                    "1D Change",
                    format="%.2f%%"
                ),
                "RSI": st.column_config.NumberColumn(
                    "RSI",
                    format="%.1f"
                ),
                "Trend": "Trend",
                "Recommendation": "AI Rating",
                "Score": st.column_config.NumberColumn(
                    "Score",
                    format="%d/10"
                ),
                "Signals": st.column_config.NumberColumn(
                    "Signals (90d)",
                    format="%d"
                )
            },
            hide_index=True,
            use_container_width=True
        )
        
        # Quick stats
        st.divider()
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            bullish_count = len([s for s in watchlist_data if '🟢' in s['Trend']])
            st.metric("Bullish Stocks", bullish_count)
        
        with col2:
            bearish_count = len([s for s in watchlist_data if '🔴' in s['Trend']])
            st.metric("Bearish Stocks", bearish_count)
        
        with col3:
            avg_rsi = np.mean([s['RSI'] for s in watchlist_data])
            st.metric("Avg RSI", f"{avg_rsi:.1f}")
        
        with col4:
            total_signals = sum([s['Signals'] for s in watchlist_data])
            st.metric("Total Signals", total_signals)
        
        # Export watchlist
        csv_watchlist = watchlist_df.to_csv(index=False)
        st.download_button(
            label="📥 Export Watchlist",
            data=csv_watchlist,
            file_name=f"watchlist_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )

# Footer
st.divider()
st.caption("🔍 Stock Research | Real-time technical analysis | Data refreshed on scan")
