"""
Advanced Portfolio Optimizer
Implements multiple allocation strategies for comparison
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
from datetime import datetime, timedelta

class PortfolioOptimizer:
    """
    Multi-strategy portfolio optimizer supporting:
    - Equal Weight
    - Risk Parity
    - Maximum Sharpe Ratio
    - Minimum Variance
    - Momentum Weighted
    - Kelly Criterion
    """
    
    def __init__(self, returns_df: pd.DataFrame, risk_free_rate: float = 0.06):
        """
        Args:
            returns_df: DataFrame with stock returns (columns = tickers, index = dates)
            risk_free_rate: Annual risk-free rate (default 6% for India)
        """
        self.returns = returns_df
        self.risk_free_rate = risk_free_rate
        self.mean_returns = returns_df.mean() * 252  # Annualized
        self.cov_matrix = returns_df.cov() * 252  # Annualized
        
    def equal_weight(self) -> Dict[str, float]:
        """Equal allocation across all stocks"""
        n_stocks = len(self.returns.columns)
        return {stock: 1.0 / n_stocks for stock in self.returns.columns}
    
    def risk_parity(self) -> Dict[str, float]:
        """
        Risk Parity: Equal risk contribution from each asset
        Inverse volatility weighting
        """
        volatilities = np.sqrt(np.diag(self.cov_matrix))
        inv_vol = 1.0 / volatilities
        weights = inv_vol / inv_vol.sum()
        return dict(zip(self.returns.columns, weights))
    
    def minimum_variance(self) -> Dict[str, float]:
        """
        Minimum Variance Portfolio
        Minimize portfolio volatility
        """
        n = len(self.mean_returns)
        
        # Objective: minimize w' * Cov * w
        # Constraint: sum(w) = 1, w >= 0
        
        # Using quadratic programming approximation
        inv_cov = np.linalg.pinv(self.cov_matrix.values)
        ones = np.ones(n)
        
        weights = inv_cov @ ones
        weights = weights / weights.sum()
        weights = np.maximum(weights, 0)  # No shorting
        weights = weights / weights.sum()  # Renormalize
        
        return dict(zip(self.returns.columns, weights))
    
    def maximum_sharpe(self, max_iter: int = 1000) -> Dict[str, float]:
        """
        Maximum Sharpe Ratio Portfolio
        Uses efficient frontier optimization
        """
        n = len(self.mean_returns)
        
        # Random search for max Sharpe
        best_sharpe = -np.inf
        best_weights = None
        
        for _ in range(max_iter):
            # Random weights
            w = np.random.random(n)
            w = w / w.sum()
            
            # Portfolio metrics
            ret = w @ self.mean_returns
            vol = np.sqrt(w @ self.cov_matrix @ w)
            sharpe = (ret - self.risk_free_rate) / vol
            
            if sharpe > best_sharpe:
                best_sharpe = sharpe
                best_weights = w
        
        return dict(zip(self.returns.columns, best_weights))
    
    def momentum_weighted(self, lookback_days: int = 90) -> Dict[str, float]:
        """
        Momentum-based allocation
        Weight by recent performance (last N days)
        """
        # Calculate momentum scores (recent returns)
        momentum = self.returns.tail(lookback_days).sum()
        
        # Only positive momentum stocks
        positive_momentum = momentum[momentum > 0]
        
        if len(positive_momentum) == 0:
            # Fallback to equal weight if no positive momentum
            return self.equal_weight()
        
        # Normalize weights
        weights = positive_momentum / positive_momentum.sum()
        
        # Fill missing stocks with 0
        all_weights = {stock: 0.0 for stock in self.returns.columns}
        all_weights.update(weights.to_dict())
        
        return all_weights
    
    def kelly_criterion(self, max_allocation: float = 0.25) -> Dict[str, float]:
        """
        Kelly Criterion for position sizing
        f* = (p*b - q) / b, where p = win rate, q = loss rate, b = win/loss ratio
        
        Approximation using returns distribution
        """
        kelly_weights = {}
        
        for stock in self.returns.columns:
            stock_returns = self.returns[stock].dropna()
            
            if len(stock_returns) == 0:
                kelly_weights[stock] = 0.0
                continue
            
            # Win/loss statistics
            wins = stock_returns[stock_returns > 0]
            losses = stock_returns[stock_returns < 0]
            
            if len(wins) == 0 or len(losses) == 0:
                kelly_weights[stock] = 0.0
                continue
            
            p = len(wins) / len(stock_returns)  # Win rate
            q = 1 - p  # Loss rate
            
            avg_win = wins.mean()
            avg_loss = abs(losses.mean())
            
            if avg_loss == 0:
                kelly_weights[stock] = 0.0
                continue
            
            b = avg_win / avg_loss  # Win/loss ratio
            
            # Kelly formula
            kelly_f = (p * b - q) / b
            
            # Cap at max_allocation and ensure non-negative
            kelly_f = max(0, min(kelly_f, max_allocation))
            
            kelly_weights[stock] = kelly_f
        
        # Normalize
        total = sum(kelly_weights.values())
        if total > 0:
            kelly_weights = {k: v/total for k, v in kelly_weights.items()}
        else:
            kelly_weights = self.equal_weight()
        
        return kelly_weights
    
    def calculate_portfolio_metrics(self, weights: Dict[str, float]) -> Dict[str, float]:
        """
        Calculate portfolio performance metrics
        
        Returns:
            Dictionary with return, volatility, sharpe, max_drawdown
        """
        w = np.array([weights.get(stock, 0) for stock in self.returns.columns])
        
        # Portfolio return and volatility
        portfolio_return = w @ self.mean_returns
        portfolio_vol = np.sqrt(w @ self.cov_matrix @ w)
        sharpe = (portfolio_return - self.risk_free_rate) / portfolio_vol if portfolio_vol > 0 else 0
        
        # Calculate max drawdown
        portfolio_cumulative = (self.returns @ w).cumsum()
        running_max = portfolio_cumulative.expanding().max()
        drawdown = portfolio_cumulative - running_max
        max_drawdown = drawdown.min()
        
        return {
            'annual_return': portfolio_return,
            'annual_volatility': portfolio_vol,
            'sharpe_ratio': sharpe,
            'max_drawdown': max_drawdown
        }
    
    def project_growth(self, 
                      initial_capital: float, 
                      target_capital: float,
                      weights: Dict[str, float],
                      years: int = 10) -> Dict:
        """
        Project portfolio growth over time
        
        Returns:
            Dictionary with projected values and timeline
        """
        metrics = self.calculate_portfolio_metrics(weights)
        annual_return = metrics['annual_return']
        
        # Calculate required CAGR
        required_cagr = (target_capital / initial_capital) ** (1/years) - 1
        
        # Project year-by-year
        projections = []
        current = initial_capital
        
        for year in range(years + 1):
            projections.append({
                'year': year,
                'value': current,
                'required_value': initial_capital * ((1 + required_cagr) ** year)
            })
            current = current * (1 + annual_return)
        
        # Years to reach target
        if annual_return > 0:
            years_to_target = np.log(target_capital / initial_capital) / np.log(1 + annual_return)
        else:
            years_to_target = np.inf
        
        return {
            'projections': projections,
            'years_to_target': years_to_target,
            'final_value': current,
            'required_cagr': required_cagr,
            'projected_cagr': annual_return
        }
    
    def compare_all_strategies(self) -> pd.DataFrame:
        """
        Compare all allocation strategies
        
        Returns:
            DataFrame with strategy comparison
        """
        strategies = {
            'Equal Weight': self.equal_weight(),
            'Risk Parity': self.risk_parity(),
            'Minimum Variance': self.minimum_variance(),
            'Maximum Sharpe': self.maximum_sharpe(),
            'Momentum Weighted': self.momentum_weighted(),
            'Kelly Criterion': self.kelly_criterion()
        }
        
        results = []
        
        for name, weights in strategies.items():
            metrics = self.calculate_portfolio_metrics(weights)
            
            results.append({
                'Strategy': name,
                'Annual Return': f"{metrics['annual_return']:.2%}",
                'Annual Volatility': f"{metrics['annual_volatility']:.2%}",
                'Sharpe Ratio': f"{metrics['sharpe_ratio']:.3f}",
                'Max Drawdown': f"{metrics['max_drawdown']:.2%}",
                'Return/Vol': metrics['annual_return'] / metrics['annual_volatility'] if metrics['annual_volatility'] > 0 else 0
            })
        
        return pd.DataFrame(results)


def calculate_stock_returns(price_data: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate daily returns from price data
    
    Args:
        price_data: DataFrame with prices (columns = tickers, index = dates)
    
    Returns:
        DataFrame with daily returns
    """
    return price_data.pct_change().dropna()
