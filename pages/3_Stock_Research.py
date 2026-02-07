"""
Enhanced Stock Research Page
Advanced technical analysis with multiple indicators and comparison features
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
st.title("🔍 Stock Research")
st.markdown("**Advanced Technical Analysis with Multiple Indicators**")

# Check database
available_stocks = get_all_stocks()

if not available_stocks:
    st.error("⚠️ No stock data found. Please run `python run_scan.py` first.")
    st.stop()

st.success(f"✅ {len(available_stocks)} stocks available for research")

st.divider()

# Main layout
tab1, tab2, tab3 = st.tabs(["📊 Single Stock Analysis", "⚖️ Compare Stocks", "📋 Watchlist"])

# ============================================================================
# TAB 1: SINGLE STOCK ANALYSIS
# ============================================================================

with tab1:
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Stock selector with search
        selected_stock = st.selectbox(
            "Select Stock",
            options=available_stocks,
            index=0,
            help="Type to search stocks"
        )
    
    with col2:
        chart_type = st.selectbox(
            "Chart Type",
            options=['Candlestick', 'Line'],
            index=0
        )
        
        days_to_show = st.selectbox(
            "Time Period",
            options=[30, 90, 180, 365],
            format_func=lambda x: f"{x} days" if x < 365 else "1 year",
            index=3
        )
    
    if selected_stock:
        # Load data
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
# TAB 2: COMPARE STOCKS
# ============================================================================

with tab2:
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
# TAB 3: WATCHLIST
# ============================================================================

with tab3:
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
