"""
Enhanced Strategy Comparison Page
Compares multiple portfolio allocation strategies with backtesting
"""

import streamlit as st
import pandas as pd
import numpy as np
import sqlite3
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from portfolio_optimizer import PortfolioOptimizer, calculate_stock_returns

st.set_page_config(page_title="Strategy Comparison", page_icon="⚖️", layout="wide")

st.title("⚖️ Advanced Strategy Comparison")
st.markdown("Compare multiple portfolio allocation strategies to maximize returns")

# Database connection
DB_PATH = "scan_results.db"

@st.cache_data(ttl=300)
def load_stock_data():
    """Load all stock data from database"""
    conn = sqlite3.connect(DB_PATH)
    
    # Get all available stocks
    stocks_df = pd.read_sql_query("SELECT DISTINCT ticker FROM scan_results", conn)
    tickers = stocks_df['ticker'].tolist()
    
    # Load price data for all stocks
    all_prices = {}
    
    for ticker in tickers:
        query = f"""
        SELECT date, close_price 
        FROM scan_results 
        WHERE ticker = '{ticker}'
        ORDER BY date
        """
        df = pd.read_sql_query(query, conn)
        
        if len(df) > 0:
            df['date'] = pd.to_datetime(df['date'])
            df = df.set_index('date')
            all_prices[ticker] = df['close_price']
    
    conn.close()
    
    # Combine into single DataFrame
    if all_prices:
        price_df = pd.DataFrame(all_prices)
        return price_df
    else:
        return pd.DataFrame()

# Load data
price_data = load_stock_data()

if price_data.empty:
    st.warning("⚠️ No stock data found. Please run `python run_scan.py` first.")
    st.stop()

# Sidebar configuration
st.sidebar.header("⚙️ Configuration")

initial_capital = st.sidebar.number_input(
    "Initial Capital (₹)",
    min_value=100000,
    max_value=100000000,
    value=2000000,
    step=100000,
    format="%d"
)

target_capital = st.sidebar.number_input(
    "Target Capital (₹)",
    min_value=initial_capital,
    max_value=1000000000,
    value=10000000,
    step=100000,
    format="%d"
)

investment_horizon = st.sidebar.slider(
    "Investment Horizon (years)",
    min_value=1,
    max_value=20,
    value=10
)

risk_free_rate = st.sidebar.slider(
    "Risk-Free Rate (%)",
    min_value=3.0,
    max_value=10.0,
    value=6.5,
    step=0.5
) / 100

# Calculate returns
returns_data = calculate_stock_returns(price_data)

# Initialize optimizer
optimizer = PortfolioOptimizer(returns_data, risk_free_rate=risk_free_rate)

# Calculate required CAGR
required_cagr = (target_capital / initial_capital) ** (1 / investment_horizon) - 1

st.markdown(f"""
### 🎯 Investment Goal
- **Initial Capital:** ₹{initial_capital:,.0f}
- **Target Capital:** ₹{target_capital:,.0f}
- **Horizon:** {investment_horizon} years
- **Required CAGR:** {required_cagr:.2%}
""")

st.divider()

# Calculate all strategies
with st.spinner("Calculating optimal allocations..."):
    strategies = {
        'Equal Weight': optimizer.equal_weight(),
        'Risk Parity': optimizer.risk_parity(),
        'Minimum Variance': optimizer.minimum_variance(),
        'Maximum Sharpe': optimizer.maximum_sharpe(),
        'Momentum Weighted': optimizer.momentum_weighted(),
        'Kelly Criterion': optimizer.kelly_criterion()
    }
    
    # Calculate metrics for each strategy
    strategy_metrics = {}
    for name, weights in strategies.items():
        metrics = optimizer.calculate_portfolio_metrics(weights)
        projection = optimizer.project_growth(initial_capital, target_capital, weights, investment_horizon)
        
        strategy_metrics[name] = {
            **metrics,
            'weights': weights,
            'projection': projection
        }

# Display strategy comparison table
st.header("📊 Strategy Performance Comparison")

comparison_data = []
for name, data in strategy_metrics.items():
    comparison_data.append({
        'Strategy': name,
        'Annual Return': data['annual_return'],
        'Annual Volatility': data['annual_volatility'],
        'Sharpe Ratio': data['sharpe_ratio'],
        'Max Drawdown': data['max_drawdown'],
        'Years to Target': data['projection']['years_to_target'],
        'Final Value (10Y)': data['projection']['final_value']
    })

comparison_df = pd.DataFrame(comparison_data)

# Highlight best strategy
best_sharpe_idx = comparison_df['Sharpe Ratio'].idxmax()
best_return_idx = comparison_df['Annual Return'].idxmax()

# Format for display
display_df = comparison_df.copy()
display_df['Annual Return'] = display_df['Annual Return'].apply(lambda x: f"{x:.2%}")
display_df['Annual Volatility'] = display_df['Annual Volatility'].apply(lambda x: f"{x:.2%}")
display_df['Sharpe Ratio'] = display_df['Sharpe Ratio'].apply(lambda x: f"{x:.3f}")
display_df['Max Drawdown'] = display_df['Max Drawdown'].apply(lambda x: f"{x:.2%}")
display_df['Years to Target'] = display_df['Years to Target'].apply(
    lambda x: f"{x:.1f}" if x != np.inf else "Never"
)
display_df['Final Value (10Y)'] = display_df['Final Value (10Y)'].apply(lambda x: f"₹{x:,.0f}")

st.dataframe(
    display_df,
    use_container_width=True,
    hide_index=True
)

# Show recommendations
col1, col2 = st.columns(2)

with col1:
    best_sharpe_strategy = comparison_df.iloc[best_sharpe_idx]['Strategy']
    st.success(f"🏆 **Best Risk-Adjusted:** {best_sharpe_strategy}")

with col2:
    best_return_strategy = comparison_df.iloc[best_return_idx]['Strategy']
    st.info(f"📈 **Highest Return:** {best_return_strategy}")

st.divider()

# Growth Projection Chart
st.header("📈 Growth Projections")

fig = go.Figure()

# Required growth line
years = list(range(investment_horizon + 1))
required_values = [initial_capital * ((1 + required_cagr) ** y) for y in years]

fig.add_trace(go.Scatter(
    x=years,
    y=required_values,
    mode='lines',
    name='Required Path',
    line=dict(color='red', width=2, dash='dash')
))

# Add each strategy projection
colors = ['blue', 'green', 'purple', 'orange', 'brown', 'pink']

for (name, data), color in zip(strategy_metrics.items(), colors):
    proj = data['projection']['projections']
    projection_years = [p['year'] for p in proj]
    projection_values = [p['value'] for p in proj]
    
    fig.add_trace(go.Scatter(
        x=projection_years,
        y=projection_values,
        mode='lines+markers',
        name=name,
        line=dict(color=color, width=2)
    ))

fig.add_hline(
    y=target_capital, 
    line_dash="dot", 
    line_color="gray",
    annotation_text=f"Target: ₹{target_capital:,.0f}"
)

fig.update_layout(
    title="Portfolio Growth Projections",
    xaxis_title="Years",
    yaxis_title="Portfolio Value (₹)",
    hovermode='x unified',
    height=500
)

st.plotly_chart(fig, use_container_width=True)

st.divider()

# Detailed allocation view
st.header("🎯 Allocation Details")

selected_strategy = st.selectbox(
    "Select Strategy to View Allocation",
    options=list(strategies.keys())
)

weights = strategies[selected_strategy]
metrics = strategy_metrics[selected_strategy]

col1, col2 = st.columns([2, 1])

with col1:
    # Allocation pie chart
    allocation_df = pd.DataFrame([
        {'Stock': k, 'Weight': v} 
        for k, v in weights.items() 
        if v > 0.001  # Filter out negligible allocations
    ]).sort_values('Weight', ascending=False)
    
    fig_pie = go.Figure(data=[go.Pie(
        labels=allocation_df['Stock'],
        values=allocation_df['Weight'],
        hole=0.3
    )])
    
    fig_pie.update_layout(
        title=f"{selected_strategy} - Stock Allocation",
        height=400
    )
    
    st.plotly_chart(fig_pie, use_container_width=True)

with col2:
    st.markdown("### Portfolio Metrics")
    st.metric("Annual Return", f"{metrics['annual_return']:.2%}")
    st.metric("Annual Volatility", f"{metrics['annual_volatility']:.2%}")
    st.metric("Sharpe Ratio", f"{metrics['sharpe_ratio']:.3f}")
    st.metric("Max Drawdown", f"{metrics['max_drawdown']:.2%}")
    
    years_to_target = metrics['projection']['years_to_target']
    if years_to_target != np.inf:
        st.metric("Years to ₹1Cr", f"{years_to_target:.1f}")
    else:
        st.metric("Years to ₹1Cr", "Never")

# Allocation table
st.markdown("### Position Sizes")

allocation_display = allocation_df.copy()
allocation_display['Capital Allocation'] = (allocation_display['Weight'] * initial_capital).apply(
    lambda x: f"₹{x:,.0f}"
)
allocation_display['Weight'] = allocation_display['Weight'].apply(lambda x: f"{x:.2%}")

st.dataframe(
    allocation_display,
    use_container_width=True,
    hide_index=True
)

st.divider()

# Efficient Frontier (if applicable)
st.header("📐 Risk-Return Analysis")

# Calculate portfolio metrics for all strategies
risk_return_data = []
for name, data in strategy_metrics.items():
    risk_return_data.append({
        'Strategy': name,
        'Return': data['annual_return'],
        'Volatility': data['annual_volatility'],
        'Sharpe': data['sharpe_ratio']
    })

risk_return_df = pd.DataFrame(risk_return_data)

fig_scatter = go.Figure()

fig_scatter.add_trace(go.Scatter(
    x=risk_return_df['Volatility'],
    y=risk_return_df['Return'],
    mode='markers+text',
    marker=dict(
        size=risk_return_df['Sharpe'] * 30,  # Size by Sharpe
        color=risk_return_df['Sharpe'],
        colorscale='Viridis',
        showscale=True,
        colorbar=dict(title="Sharpe Ratio")
    ),
    text=risk_return_df['Strategy'],
    textposition='top center',
    hovertemplate='<b>%{text}</b><br>Return: %{y:.2%}<br>Volatility: %{x:.2%}<extra></extra>'
))

fig_scatter.update_layout(
    title="Risk-Return Profile of Strategies",
    xaxis_title="Annual Volatility (Risk)",
    yaxis_title="Annual Return",
    height=500,
    xaxis=dict(tickformat='.1%'),
    yaxis=dict(tickformat='.1%')
)

st.plotly_chart(fig_scatter, use_container_width=True)

# Footer
st.divider()
st.markdown("""
**⚠️ Disclaimer:** This is for educational purposes only. Past performance does not guarantee future results.
All projections are based on historical data and may not reflect actual future performance.
""")
