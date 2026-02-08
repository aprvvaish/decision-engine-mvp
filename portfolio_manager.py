"""
Portfolio Manager - Save, Load, and Compare Portfolios
"""

import sqlite3
import pandas as pd
import json
from datetime import datetime
from typing import Dict, List, Optional

DB_PATH = "scan_results.db"

class PortfolioManager:
    """
    Manage saved portfolios: create, load, delete, compare
    """
    
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._create_table()
    
    def _create_table(self):
        """Create portfolios table if not exists"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS portfolios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                description TEXT,
                initial_capital REAL NOT NULL,
                target_capital REAL,
                allocations TEXT NOT NULL,
                strategy TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                performance_metrics TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def save_portfolio(self, 
                      name: str,
                      allocations: Dict[str, float],
                      initial_capital: float,
                      target_capital: Optional[float] = None,
                      description: str = "",
                      strategy: str = "",
                      performance_metrics: Optional[Dict] = None) -> bool:
        """
        Save a portfolio to database
        
        Args:
            name: Unique portfolio name
            allocations: Dict of {ticker: weight}
            initial_capital: Starting capital
            target_capital: Goal capital (optional)
            description: Portfolio description
            strategy: Strategy used
            performance_metrics: Performance data (optional)
        
        Returns:
            True if saved successfully
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Convert allocations and metrics to JSON
            allocations_json = json.dumps(allocations)
            metrics_json = json.dumps(performance_metrics) if performance_metrics else None
            
            # Check if portfolio exists
            cursor.execute("SELECT id FROM portfolios WHERE name = ?", (name,))
            existing = cursor.fetchone()
            
            if existing:
                # Update existing
                cursor.execute('''
                    UPDATE portfolios 
                    SET description = ?,
                        initial_capital = ?,
                        target_capital = ?,
                        allocations = ?,
                        strategy = ?,
                        updated_at = ?,
                        performance_metrics = ?
                    WHERE name = ?
                ''', (description, initial_capital, target_capital, 
                      allocations_json, strategy, now, metrics_json, name))
            else:
                # Insert new
                cursor.execute('''
                    INSERT INTO portfolios 
                    (name, description, initial_capital, target_capital, 
                     allocations, strategy, created_at, updated_at, performance_metrics)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (name, description, initial_capital, target_capital,
                      allocations_json, strategy, now, now, metrics_json))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"Error saving portfolio: {e}")
            return False
    
    def load_portfolio(self, name: str) -> Optional[Dict]:
        """
        Load a portfolio by name
        
        Returns:
            Dictionary with portfolio data or None if not found
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT name, description, initial_capital, target_capital,
                       allocations, strategy, created_at, updated_at, 
                       performance_metrics
                FROM portfolios 
                WHERE name = ?
            ''', (name,))
            
            row = cursor.fetchone()
            conn.close()
            
            if not row:
                return None
            
            return {
                'name': row[0],
                'description': row[1],
                'initial_capital': row[2],
                'target_capital': row[3],
                'allocations': json.loads(row[4]),
                'strategy': row[5],
                'created_at': row[6],
                'updated_at': row[7],
                'performance_metrics': json.loads(row[8]) if row[8] else {}
            }
            
        except Exception as e:
            print(f"Error loading portfolio: {e}")
            return None
    
    def list_portfolios(self) -> pd.DataFrame:
        """
        Get list of all saved portfolios
        
        Returns:
            DataFrame with portfolio summaries
        """
        try:
            conn = sqlite3.connect(self.db_path)
            
            df = pd.read_sql_query('''
                SELECT name, description, initial_capital, target_capital,
                       strategy, created_at, updated_at
                FROM portfolios
                ORDER BY updated_at DESC
            ''', conn)
            
            conn.close()
            return df
            
        except Exception as e:
            print(f"Error listing portfolios: {e}")
            return pd.DataFrame()
    
    def delete_portfolio(self, name: str) -> bool:
        """Delete a portfolio by name"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM portfolios WHERE name = ?", (name,))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"Error deleting portfolio: {e}")
            return False
    
    def compare_portfolios(self, portfolio_names: List[str]) -> pd.DataFrame:
        """
        Compare multiple portfolios
        
        Args:
            portfolio_names: List of portfolio names to compare
        
        Returns:
            DataFrame with comparison data
        """
        portfolios = []
        
        for name in portfolio_names:
            portfolio = self.load_portfolio(name)
            if portfolio:
                # Calculate portfolio metrics
                allocations = portfolio['allocations']
                n_stocks = len([v for v in allocations.values() if v > 0])
                max_position = max(allocations.values()) if allocations else 0
                
                portfolios.append({
                    'Name': name,
                    'Strategy': portfolio['strategy'],
                    'Initial Capital': portfolio['initial_capital'],
                    'Target Capital': portfolio['target_capital'] or 'N/A',
                    'Num Stocks': n_stocks,
                    'Max Position': f"{max_position:.1%}",
                    'Created': portfolio['created_at'],
                    'Updated': portfolio['updated_at']
                })
        
        return pd.DataFrame(portfolios)
    
    def get_portfolio_history(self, name: str) -> List[Dict]:
        """
        Get historical performance data for a portfolio
        
        Note: In a real system, this would track daily values
        For now, returns empty list as placeholder
        """
        # TODO: Implement portfolio value tracking over time
        return []


def calculate_portfolio_value(allocations: Dict[str, float], 
                              capital: float,
                              current_prices: Dict[str, float]) -> Dict:
    """
    Calculate current portfolio value based on allocations
    
    Args:
        allocations: Dict of {ticker: weight}
        capital: Initial capital invested
        current_prices: Dict of {ticker: current_price}
    
    Returns:
        Dictionary with portfolio value breakdown
    """
    total_current_value = 0
    total_allocated = 0
    positions = {}
    
    for ticker, weight in allocations.items():
        if weight > 0:
            allocation_amount = capital * weight
            total_allocated += allocation_amount
            
            if ticker in current_prices:
                current_price = current_prices[ticker]
                # Assuming shares bought at initial allocation
                # In real system, would track purchase price
                current_value = allocation_amount  # Simplified
                
                positions[ticker] = {
                    'weight': weight,
                    'allocated': allocation_amount,
                    'current_value': current_value,
                    'current_price': current_price
                }
                
                total_current_value += current_value
    
    cash = capital - total_allocated
    total_value = total_current_value + cash
    
    gain_loss = total_current_value - total_allocated
    gain_loss_pct = (gain_loss / total_allocated * 100) if total_allocated > 0 else 0
    
    return {
        'total_value': total_value,
        'invested_value': total_allocated,
        'current_value': total_current_value,
        'cash': cash,
        'gain_loss': gain_loss,
        'gain_loss_pct': gain_loss_pct,
        'positions': positions
    }


def calculate_portfolio_performance(portfolio_name: str, 
                                   current_prices: Dict[str, float],
                                   db_path: str = DB_PATH) -> Dict:
    """
    Calculate real-time performance of a saved portfolio
    
    Args:
        portfolio_name: Name of the portfolio
        current_prices: Dict of current stock prices
        db_path: Database path
    
    Returns:
        Dict with performance metrics
    """
    pm = PortfolioManager(db_path)
    portfolio = pm.load_portfolio(portfolio_name)
    
    if not portfolio:
        return None
    
    allocations = portfolio['allocations']
    initial_capital = portfolio['initial_capital']
    created_at = portfolio.get('created_at', '')
    
    # Extract date from created_at (format: "2026-02-08 14:30:00")
    creation_date = created_at.split(' ')[0] if created_at else None
    
    # Calculate current value for each position
    current_value = 0
    invested_value = 0
    positions_detail = []
    
    conn = sqlite3.connect(db_path)
    
    for ticker, weight in allocations.items():
        if weight > 0:
            allocation_amount = initial_capital * weight
            invested_value += allocation_amount
            
            if ticker in current_prices:
                current_price = current_prices[ticker]
                
                # Get price at portfolio creation date (or closest date before)
                if creation_date:
                    query = f"""
                    SELECT close_price, date 
                    FROM scan_results 
                    WHERE ticker = '{ticker}' 
                    AND date <= '{creation_date}'
                    ORDER BY date DESC
                    LIMIT 1
                    """
                else:
                    # Fallback: use earliest available price
                    query = f"""
                    SELECT close_price, date 
                    FROM scan_results 
                    WHERE ticker = '{ticker}' 
                    ORDER BY date ASC 
                    LIMIT 1
                    """
                
                df = pd.read_sql_query(query, conn)
                
                if not df.empty:
                    purchase_price = df.iloc[0]['close_price']
                    purchase_date = df.iloc[0]['date']
                    
                    # Calculate shares bought at creation
                    shares = allocation_amount / purchase_price
                    
                    # Calculate current value
                    position_current_value = shares * current_price
                    
                    # Calculate gain/loss
                    position_gain = position_current_value - allocation_amount
                    position_gain_pct = (position_gain / allocation_amount * 100) if allocation_amount > 0 else 0
                    
                    positions_detail.append({
                        'ticker': ticker,
                        'weight': weight,
                        'invested': allocation_amount,
                        'purchase_price': purchase_price,
                        'purchase_date': purchase_date,
                        'shares': shares,
                        'current_price': current_price,
                        'current_value': position_current_value,
                        'gain_loss': position_gain,
                        'gain_loss_pct': position_gain_pct
                    })
                    
                    current_value += position_current_value
                else:
                    # No historical data - assume no change
                    positions_detail.append({
                        'ticker': ticker,
                        'weight': weight,
                        'invested': allocation_amount,
                        'purchase_price': current_price,
                        'purchase_date': 'N/A',
                        'shares': allocation_amount / current_price if current_price > 0 else 0,
                        'current_price': current_price,
                        'current_value': allocation_amount,
                        'gain_loss': 0,
                        'gain_loss_pct': 0
                    })
                    
                    current_value += allocation_amount
    
    conn.close()
    
    # Calculate portfolio totals
    total_gain = current_value - invested_value
    total_gain_pct = (total_gain / invested_value * 100) if invested_value > 0 else 0
    
    # Cash component (unallocated capital)
    cash = initial_capital - invested_value
    total_portfolio_value = current_value + cash
    
    return {
        'portfolio_name': portfolio_name,
        'initial_capital': initial_capital,
        'invested_value': invested_value,
        'current_value': current_value,
        'cash': cash,
        'total_value': total_portfolio_value,
        'total_gain': total_gain,
        'total_gain_pct': total_gain_pct,
        'positions': positions_detail,
        'created_at': created_at,
        'creation_date': creation_date
    }
