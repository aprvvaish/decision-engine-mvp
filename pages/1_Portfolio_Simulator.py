"""
Enhanced Portfolio Simulator
Create, save, load, and compare portfolios
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

from portfolio_manager import PortfolioManager, calculate_portfolio_value

st.set_page_config(page_title="Portfolio Simulator", page_icon="🧪", layout="wide")

st.title("🧪 Portfolio Simulator")

# Initialize portfolio manager
pm = PortfolioManager()

# Tabs for different views
tab1, tab2, tab3 = st.tabs(["Create Portfolio", "Saved Portfolios", "Compare Portfolios"])

# Database connection
DB_PATH = "scan_results.db"

@st.cache_data(ttl=300)
def load_latest_prices():
    """Load latest stock prices from database"""
    conn = sqlite3.connect(DB_PATH)
    
    query = """
    SELECT ticker, close_price, date
    FROM scan_results
    WHERE date IN (
        SELECT MAX(date) FROM scan_results GROUP BY ticker
    )
    ORDER BY ticker
    """
    
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    if df.empty:
        return {}
    
    return dict(zip(df['ticker'], df['close_price']))

@st.cache_data(ttl=300)
def get_stock_signals():
    """Get stocks with recent signals"""
    conn = sqlite3.connect(DB_PATH)
    
    query = """
    SELECT DISTINCT ticker, 
           SUM(buy_signal) as buy_signals,
           SUM(momentum_signal) as momentum_signals
    FROM scan_results
    WHERE date >= date('now', '-30 days')
    GROUP BY ticker
    HAVING buy_signals > 0 OR momentum_signals > 0
    ORDER BY momentum_signals DESC, buy_signals DESC
    """
    
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    return df

# Load data
latest_prices = load_latest_prices()
signal_stocks = get_stock_signals()

if not latest_prices:
    st.warning("⚠️ No stock data found. Please run `python run_scan.py` first.")
    st.stop()

# ============================================================================
# TAB 1: CREATE PORTFOLIO
# ============================================================================

with tab1:
    st.header("Create New Portfolio")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Portfolio Configuration")
        
        portfolio_name = st.text_input(
            "Portfolio Name",
            placeholder="e.g., Aggressive Growth 2026"
        )
        
        portfolio_description = st.text_area(
            "Description (optional)",
            placeholder="Long-term growth portfolio with tech focus..."
        )
        
        initial_capital = st.number_input(
            "Initial Capital (₹)",
            min_value=10000,
            max_value=100000000,
            value=2000000,
            step=100000,
            format="%d"
        )
        
        target_capital = st.number_input(
            "Target Capital (₹, optional)",
            min_value=0,
            max_value=1000000000,
            value=10000000,
            step=100000,
            format="%d"
        )
        
        max_position_pct = st.slider(
            "Max Position Size (%)",
            min_value=1,
            max_value=25,
            value=10
        ) / 100
        
        strategy_type = st.selectbox(
            "Strategy Template",
            ["Custom", "Equal Weight", "Signal-Based", "Top Performers"]
        )
    
    with col2:
        st.subheader("Recent Signals")
        if not signal_stocks.empty:
            st.dataframe(
                signal_stocks.head(10),
                hide_index=True,
                use_container_width=True
            )
        else:
            st.info("No recent signals")
    
    st.divider()
    
    # Stock Selection
    st.subheader("Select Stocks")
    
    available_stocks = sorted(latest_prices.keys())
    
    if strategy_type == "Signal-Based" and not signal_stocks.empty:
        default_stocks = signal_stocks['ticker'].head(10).tolist()
    else:
        default_stocks = available_stocks[:10]
    
    selected_stocks = st.multiselect(
        "Choose stocks for your portfolio",
        options=available_stocks,
        default=default_stocks,
        help="Select 5-30 stocks for proper diversification"
    )
    
    if len(selected_stocks) < 5:
        st.warning("⚠️ Select at least 5 stocks for proper diversification")
    
    if selected_stocks:
        st.divider()
        st.subheader("Allocation Strategy")
        
        # Auto-generate allocations based on strategy
        if strategy_type == "Equal Weight":
            allocations = {stock: 1.0 / len(selected_stocks) for stock in selected_stocks}
        
        elif strategy_type == "Signal-Based":
            # Weight by signal strength
            weights = {}
            for stock in selected_stocks:
                signal_row = signal_stocks[signal_stocks['ticker'] == stock]
                if not signal_row.empty:
                    score = (signal_row['buy_signals'].iloc[0] + 
                            signal_row['momentum_signals'].iloc[0] * 2)
                    weights[stock] = max(score, 1)
                else:
                    weights[stock] = 1
            
            total_weight = sum(weights.values())
            allocations = {k: v/total_weight for k, v in weights.items()}
        
        elif strategy_type == "Top Performers":
            # Get recent performance
            conn = sqlite3.connect(DB_PATH)
            performance = {}
            
            for stock in selected_stocks:
                query = f"""
                SELECT close_price 
                FROM scan_results 
                WHERE ticker = '{stock}'
                ORDER BY date DESC
                LIMIT 30
                """
                df = pd.read_sql_query(query, conn)
                
                if len(df) >= 2:
                    recent_return = (df.iloc[0]['close_price'] - df.iloc[-1]['close_price']) / df.iloc[-1]['close_price']
                    performance[stock] = max(recent_return, 0.01)
                else:
                    performance[stock] = 0.01
            
            conn.close()
            
            total_perf = sum(performance.values())
            allocations = {k: v/total_perf for k, v in performance.items()}
        
        else:  # Custom
            allocations = {stock: 1.0 / len(selected_stocks) for stock in selected_stocks}
        
        # Apply max position constraint
        for stock in allocations:
            if allocations[stock] > max_position_pct:
                allocations[stock] = max_position_pct
        
        # Renormalize
        total = sum(allocations.values())
        allocations = {k: v/total for k, v in allocations.items()}
        
        # Manual adjustment
        st.markdown("**Adjust Allocations:**")
        
        # Convert weights to percentages for display (multiply by 100)
        allocation_df = pd.DataFrame([
            {
                'Stock': stock,
                'Weight': allocations[stock] * 100,  # Convert to percentage
                'Capital': allocations[stock] * initial_capital,
                'Price': latest_prices.get(stock, 0),
                'Shares': int((allocations[stock] * initial_capital) / latest_prices.get(stock, 1))
            }
            for stock in selected_stocks
        ]).sort_values('Weight', ascending=False)
        
        # Editable allocations
        edited_df = st.data_editor(
            allocation_df,
            column_config={
                "Stock": st.column_config.TextColumn("Stock", disabled=True),
                "Weight": st.column_config.NumberColumn(
                    "Weight (%)",
                    format="%.2f",
                    min_value=0,
                    max_value=max_position_pct * 100,
                    step=0.5,
                    help="Enter weight as percentage (e.g., 8.5 for 8.5%)"
                ),
                "Capital": st.column_config.NumberColumn(
                    "Allocation (₹)",
                    format="₹%.0f",
                    disabled=True
                ),
                "Price": st.column_config.NumberColumn(
                    "Price (₹)",
                    format="₹%.2f",
                    disabled=True
                ),
                "Shares": st.column_config.NumberColumn(
                    "Shares",
                    disabled=True
                )
            },
            hide_index=True,
            use_container_width=True,
            key="allocation_editor"
        )
        
        # Update allocations from editor (convert back to decimal)
        final_allocations = dict(zip(edited_df['Stock'], edited_df['Weight'] / 100))
        
        # Recalculate capital and shares based on edited weights
        for idx, row in edited_df.iterrows():
            stock = row['Stock']
            weight_decimal = row['Weight'] / 100
            edited_df.at[idx, 'Capital'] = weight_decimal * initial_capital
            if latest_prices.get(stock, 0) > 0:
                edited_df.at[idx, 'Shares'] = int((weight_decimal * initial_capital) / latest_prices[stock])
        
        # Validation
        total_weight = sum(final_allocations.values())
        cash_left = (1 - total_weight) * initial_capital
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Allocated", f"{total_weight:.1%}")
        with col2:
            st.metric("Cash Reserve", f"₹{cash_left:,.0f}")
        with col3:
            st.metric("Number of Stocks", len(selected_stocks))
        
        # Pie chart
        fig = go.Figure(data=[go.Pie(
            labels=list(final_allocations.keys()),
            values=list(final_allocations.values()),
            hole=0.3
        )])
        
        fig.update_layout(
            title="Portfolio Allocation",
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Save portfolio
        st.divider()
        
        col1, col2, col3 = st.columns([1, 1, 2])
        
        with col1:
            if st.button("💾 Save Portfolio", type="primary", use_container_width=True):
                if not portfolio_name:
                    st.error("Please enter a portfolio name")
                else:
                    # Prepare performance metrics
                    metrics = {
                        'num_stocks': len(selected_stocks),
                        'total_allocated': total_weight,
                        'cash_reserve': cash_left,
                        'max_position': max(final_allocations.values()),
                        'avg_position': np.mean(list(final_allocations.values()))
                    }
                    
                    success = pm.save_portfolio(
                        name=portfolio_name,
                        allocations=final_allocations,
                        initial_capital=initial_capital,
                        target_capital=target_capital if target_capital > 0 else None,
                        description=portfolio_description,
                        strategy=strategy_type,
                        performance_metrics=metrics
                    )
                    
                    if success:
                        st.success(f"✅ Portfolio '{portfolio_name}' saved successfully!")
                        st.balloons()
                    else:
                        st.error("Failed to save portfolio. Name might already exist.")
        
        with col2:
            if st.button("🔄 Reset", use_container_width=True):
                st.rerun()

# ============================================================================
# TAB 2: SAVED PORTFOLIOS
# ============================================================================

with tab2:
    st.header("Saved Portfolios")
    
    portfolios_df = pm.list_portfolios()
    
    if portfolios_df.empty:
        st.info("📭 No saved portfolios yet. Create one in the 'Create Portfolio' tab!")
    else:
        # Get current prices for value calculation
        from portfolio_manager import calculate_portfolio_performance
        
        # Enhanced portfolio list with current values
        enhanced_portfolios = []
        
        for _, row in portfolios_df.iterrows():
            portfolio_name = row['name']
            performance = calculate_portfolio_performance(portfolio_name, latest_prices)
            
            if performance:
                enhanced_portfolios.append({
                    'Name': portfolio_name,
                    'Initial Capital': row['initial_capital'],
                    'Current Value': performance['total_value'],
                    'Gain/Loss': performance['total_gain'],
                    'Gain %': performance['total_gain_pct'],
                    'Strategy': row['strategy'],
                    'Created': row['created_at'],
                    'Updated': row['updated_at']
                })
            else:
                enhanced_portfolios.append({
                    'Name': portfolio_name,
                    'Initial Capital': row['initial_capital'],
                    'Current Value': row['initial_capital'],
                    'Gain/Loss': 0,
                    'Gain %': 0,
                    'Strategy': row['strategy'],
                    'Created': row['created_at'],
                    'Updated': row['updated_at']
                })
        
        enhanced_df = pd.DataFrame(enhanced_portfolios)
        
        st.dataframe(
            enhanced_df,
            column_config={
                "Name": "Portfolio Name",
                "Initial Capital": st.column_config.NumberColumn(
                    "Initial Capital",
                    format="₹%.0f"
                ),
                "Current Value": st.column_config.NumberColumn(
                    "Current Value",
                    format="₹%.0f"
                ),
                "Gain/Loss": st.column_config.NumberColumn(
                    "Gain/Loss",
                    format="₹%.0f"
                ),
                "Gain %": st.column_config.NumberColumn(
                    "Gain %",
                    format="%.2f%%"
                ),
                "Strategy": "Strategy",
                "Created": "Created",
                "Updated": "Last Updated"
            },
            hide_index=True,
            use_container_width=True
        )
        
        # Summary metrics
        st.divider()
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total_invested = sum([p['Initial Capital'] for p in enhanced_portfolios])
            st.metric("Total Invested", f"₹{total_invested:,.0f}")
        
        with col2:
            total_current = sum([p['Current Value'] for p in enhanced_portfolios])
            st.metric("Total Current Value", f"₹{total_current:,.0f}")
        
        with col3:
            total_gain = total_current - total_invested
            st.metric("Total Gain/Loss", f"₹{total_gain:,.0f}", 
                     delta=f"{(total_gain/total_invested*100):.2f}%" if total_invested > 0 else "0%")
        
        with col4:
            st.metric("Number of Portfolios", len(enhanced_portfolios))
        
        st.divider()
        
        # Load and view portfolio
        st.subheader("View Portfolio Details")
        
        selected_portfolio = st.selectbox(
            "Select Portfolio",
            options=portfolios_df['name'].tolist()
        )
        
        if selected_portfolio:
            portfolio = pm.load_portfolio(selected_portfolio)
            performance = calculate_portfolio_performance(selected_portfolio, latest_prices)
            
            if portfolio:
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.markdown(f"**Description:** {portfolio['description'] or 'N/A'}")
                    st.markdown(f"**Strategy:** {portfolio['strategy']}")
                    st.markdown(f"**Created:** {portfolio['created_at']}")
                    st.markdown(f"**Last Updated:** {portfolio['updated_at']}")
                
                with col2:
                    if performance:
                        st.metric("Initial Capital", f"₹{performance['initial_capital']:,.0f}")
                        st.metric("Current Value", f"₹{performance['total_value']:,.0f}",
                                 delta=f"{performance['total_gain_pct']:+.2f}%")
                        
                        # Color-coded gain/loss
                        if performance['total_gain'] >= 0:
                            st.success(f"💰 Gain: ₹{performance['total_gain']:,.0f}")
                        else:
                            st.error(f"📉 Loss: ₹{abs(performance['total_gain']):,.0f}")
                    else:
                        st.metric("Initial Capital", f"₹{portfolio['initial_capital']:,.0f}")
                        if portfolio['target_capital']:
                            st.metric("Target Capital", f"₹{portfolio['target_capital']:,.0f}")
                
                st.divider()
                
                # Show allocations with current values
                allocations = portfolio['allocations']
                
                if performance and performance['positions']:
                    # Enhanced allocation display with real-time values
                    allocation_display = pd.DataFrame(performance['positions'])
                    
                    allocation_display = allocation_display.rename(columns={
                        'ticker': 'Stock',
                        'weight': 'Weight',
                        'invested': 'Invested',
                        'current_value': 'Current Value',
                        'current_price': 'Current Price',
                        'gain_loss': 'Gain/Loss',
                        'gain_loss_pct': 'Gain %'
                    })
                    
                    allocation_display['Weight'] = allocation_display['Weight'] * 100
                    
                    st.dataframe(
                        allocation_display,
                        column_config={
                            "Stock": "Stock",
                            "Weight": st.column_config.NumberColumn(
                                "Weight (%)",
                                format="%.2f"
                            ),
                            "Invested": st.column_config.NumberColumn(
                                "Invested",
                                format="₹%.0f"
                            ),
                            "Current Value": st.column_config.NumberColumn(
                                "Current Value",
                                format="₹%.0f"
                            ),
                            "Current Price": st.column_config.NumberColumn(
                                "Price",
                                format="₹%.2f"
                            ),
                            "Gain/Loss": st.column_config.NumberColumn(
                                "Gain/Loss",
                                format="₹%.0f"
                            ),
                            "Gain %": st.column_config.NumberColumn(
                                "Gain %",
                                format="%.2f%%"
                            )
                        },
                        hide_index=True,
                        use_container_width=True
                    )
                else:
                    # Fallback to simple display if no performance data
                    allocation_display = pd.DataFrame([
                        {
                            'Stock': stock,
                            'Weight': weight * 100,
                            'Capital': weight * portfolio['initial_capital'],
                            'Current Price': latest_prices.get(stock, 0)
                        }
                        for stock, weight in allocations.items()
                        if weight > 0
                    ]).sort_values('Weight', ascending=False)
                    
                    st.dataframe(
                        allocation_display,
                        column_config={
                            "Stock": "Stock",
                            "Weight": st.column_config.NumberColumn(
                                "Weight (%)",
                                format="%.2f"
                            ),
                            "Capital": st.column_config.NumberColumn(
                                "Allocation",
                                format="₹%.0f"
                            ),
                            "Current Price": st.column_config.NumberColumn(
                                "Price",
                                format="₹%.2f"
                            )
                        },
                        hide_index=True,
                        use_container_width=True
                    )
                
                # Pie chart
                fig = go.Figure(data=[go.Pie(
                    labels=[k for k, v in allocations.items() if v > 0],
                    values=[v for v in allocations.values() if v > 0],
                    hole=0.3
                )])
                
                fig.update_layout(
                    title=f"{selected_portfolio} - Allocation",
                    height=400
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                # Actions
                col1, col2, col3 = st.columns([1, 1, 2])
                
                with col1:
                    if st.button("🗑️ Delete Portfolio", type="secondary"):
                        if pm.delete_portfolio(selected_portfolio):
                            st.success(f"Deleted '{selected_portfolio}'")
                            st.rerun()
                        else:
                            st.error("Failed to delete portfolio")
                
                with col2:
                    # Export to CSV
                    csv = allocation_display.to_csv(index=False)
                    st.download_button(
                        label="📥 Export CSV",
                        data=csv,
                        file_name=f"{selected_portfolio}_allocations.csv",
                        mime="text/csv"
                    )

# ============================================================================
# TAB 3: COMPARE PORTFOLIOS
# ============================================================================

with tab3:
    st.header("Compare Portfolios")
    
    portfolios_df = pm.list_portfolios()
    
    if len(portfolios_df) < 2:
        st.info("📊 You need at least 2 saved portfolios to compare. Create more in the 'Create Portfolio' tab!")
    else:
        selected_for_comparison = st.multiselect(
            "Select portfolios to compare",
            options=portfolios_df['name'].tolist(),
            default=portfolios_df['name'].head(2).tolist()
        )
        
        if len(selected_for_comparison) < 2:
            st.warning("Please select at least 2 portfolios to compare")
        else:
            # Comparison table
            comparison_df = pm.compare_portfolios(selected_for_comparison)
            
            st.dataframe(
                comparison_df,
                column_config={
                    "Initial Capital": st.column_config.NumberColumn(
                        "Initial Capital",
                        format="₹%.0f"
                    )
                },
                hide_index=True,
                use_container_width=True
            )
            
            st.divider()
            
            # Detailed comparison
            st.subheader("Allocation Comparison")
            
            # Get all unique stocks across portfolios
            all_stocks = set()
            portfolio_data = {}
            
            for pf_name in selected_for_comparison:
                portfolio = pm.load_portfolio(pf_name)
                if portfolio:
                    portfolio_data[pf_name] = portfolio
                    all_stocks.update(portfolio['allocations'].keys())
            
            # Create comparison dataframe
            comparison_allocations = []
            
            for stock in sorted(all_stocks):
                row = {'Stock': stock}
                for pf_name in selected_for_comparison:
                    if pf_name in portfolio_data:
                        weight = portfolio_data[pf_name]['allocations'].get(stock, 0)
                        row[pf_name] = weight * 100  # Convert to percentage for display
                    else:
                        row[pf_name] = 0
                comparison_allocations.append(row)
            
            comparison_alloc_df = pd.DataFrame(comparison_allocations)
            
            # Only show stocks that appear in at least one portfolio
            comparison_alloc_df = comparison_alloc_df[
                comparison_alloc_df[selected_for_comparison].sum(axis=1) > 0
            ]
            
            st.dataframe(
                comparison_alloc_df,
                column_config={
                    "Stock": "Stock",
                    **{
                        pf_name: st.column_config.NumberColumn(
                            pf_name,
                            format="%.2f"
                        )
                        for pf_name in selected_for_comparison
                    }
                },
                hide_index=True,
                use_container_width=True
            )
            
            # Side-by-side pie charts
            st.subheader("Visual Comparison")
            
            n_portfolios = len(selected_for_comparison)
            cols = st.columns(min(n_portfolios, 3))
            
            for idx, pf_name in enumerate(selected_for_comparison):
                with cols[idx % 3]:
                    if pf_name in portfolio_data:
                        allocations = portfolio_data[pf_name]['allocations']
                        
                        fig = go.Figure(data=[go.Pie(
                            labels=[k for k, v in allocations.items() if v > 0],
                            values=[v for v in allocations.values() if v > 0],
                            hole=0.3
                        )])
                        
                        fig.update_layout(
                            title=pf_name,
                            height=300,
                            showlegend=False
                        )
                        
                        st.plotly_chart(fig, use_container_width=True)
            
            # Overlap analysis
            st.divider()
            st.subheader("Portfolio Overlap Analysis")
            
            # Calculate overlap between portfolios
            overlap_data = []
            
            for i, pf1 in enumerate(selected_for_comparison):
                for pf2 in selected_for_comparison[i+1:]:
                    if pf1 in portfolio_data and pf2 in portfolio_data:
                        stocks1 = set(k for k, v in portfolio_data[pf1]['allocations'].items() if v > 0)
                        stocks2 = set(k for k, v in portfolio_data[pf2]['allocations'].items() if v > 0)
                        
                        common = stocks1 & stocks2
                        overlap_pct = len(common) / len(stocks1 | stocks2) * 100 if stocks1 | stocks2 else 0
                        
                        overlap_data.append({
                            'Portfolio 1': pf1,
                            'Portfolio 2': pf2,
                            'Common Stocks': len(common),
                            'Overlap %': overlap_pct,
                            'Common': ', '.join(sorted(common)[:5]) + ('...' if len(common) > 5 else '')
                        })
            
            if overlap_data:
                overlap_df = pd.DataFrame(overlap_data)
                
                st.dataframe(
                    overlap_df,
                    column_config={
                        "Overlap %": st.column_config.NumberColumn(
                            "Overlap %",
                            format="%.1f%%"
                        )
                    },
                    hide_index=True,
                    use_container_width=True
                )

# Footer
st.divider()
st.markdown("""
**💡 Tips:**
- Maintain 5-30 stocks for proper diversification
- Keep max position size under 10-15%
- Save different portfolio variations to compare strategies
- Review and rebalance quarterly

**⚠️ Disclaimer:** Educational purposes only. Not financial advice.
""")
