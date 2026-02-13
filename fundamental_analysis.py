"""
Fundamental Analysis Module
Fetches and analyzes company fundamentals, financials, and competitive data
"""

import yfinance as yf
import pandas as pd
import numpy as np
from typing import Dict, Optional, List
import streamlit as st
from datetime import datetime, timedelta

class FundamentalAnalyzer:
    """
    Comprehensive fundamental analysis for stocks
    
    Features:
    - Quarterly results and revenue trends
    - Valuation metrics
    - Industry comparison
    - Risk factors
    - Financial health indicators
    """
    
    def __init__(self, ticker: str):
        """
        Initialize analyzer for a stock
        
        Args:
            ticker: Stock ticker (e.g., 'RELIANCE.NS' or 'RELIANCE')
        """
        # Auto-add .NS suffix for Indian stocks if not present
        if not ticker.endswith('.NS') and not ticker.endswith('.BO'):
            ticker = f"{ticker}.NS"
        
        self.ticker = ticker
        try:
            self.stock = yf.Ticker(ticker)
        except Exception as e:
            print(f"Error initializing yfinance for {ticker}: {e}")
            self.stock = None
    
    def get_company_info(self) -> Dict:
        """Get company information"""
        try:
            if self.stock is None:
                return {'name': 'N/A', 'sector': 'N/A', 'industry': 'N/A'}
            
            info = self.stock.info
            return {
                'name': info.get('longName', info.get('shortName', 'N/A')),
                'sector': info.get('sector', 'N/A'),
                'industry': info.get('industry', 'N/A'),
                'website': info.get('website', 'N/A'),
                'description': info.get('longBusinessSummary', 'N/A'),
                'employees': info.get('fullTimeEmployees', 'N/A'),
                'country': info.get('country', 'N/A'),
                'city': info.get('city', 'N/A'),
                'market_cap': info.get('marketCap', 0),
                'currency': info.get('currency', 'INR')
            }
        except Exception as e:
            print(f"Error getting company info: {e}")
            return {'name': 'N/A', 'sector': 'N/A', 'industry': 'N/A'}
    
    def get_quarterly_results(self) -> pd.DataFrame:
        """Get quarterly financial results"""
        try:
            if self.stock is None:
                return pd.DataFrame()
            
            # Get quarterly financials
            quarterly = self.stock.quarterly_financials
            
            if quarterly is not None and not quarterly.empty:
                # Transpose so quarters are rows
                df = quarterly.T
                # Format index
                df.index = pd.to_datetime(df.index).strftime('%Y-Q%q')
                return df.head(8)  # Last 8 quarters (2 years)
            
            return pd.DataFrame()
        except Exception as e:
            print(f"Error getting quarterly results: {e}")
            return pd.DataFrame()
    
    def get_revenue_trends(self) -> Dict:
        """Get revenue growth trends"""
        try:
            if self.stock is None:
                return {'status': 'unavailable'}
            
            quarterly = self.stock.quarterly_financials
            
            if quarterly is None or quarterly.empty:
                return {'status': 'unavailable'}
            
            df = quarterly.T
            
            # Get Total Revenue
            if 'Total Revenue' in df.columns:
                revenue = df['Total Revenue'].dropna()
                
                if len(revenue) >= 2:
                    latest = revenue.iloc[0]
                    previous = revenue.iloc[1]
                    qoq_growth = ((latest - previous) / previous * 100) if previous != 0 else 0
                    
                    # YoY growth (compare with 4 quarters ago)
                    if len(revenue) >= 5:
                        year_ago = revenue.iloc[4]
                        yoy_growth = ((latest - year_ago) / year_ago * 100) if year_ago != 0 else 0
                    else:
                        yoy_growth = None
                    
                    return {
                        'status': 'available',
                        'latest_revenue': latest,
                        'qoq_growth': qoq_growth,
                        'yoy_growth': yoy_growth,
                        'revenue_trend': revenue.tolist()[:8]
                    }
            
            return {'status': 'unavailable'}
        except Exception as e:
            print(f"Error getting revenue trends: {e}")
            return {'status': 'error'}
    
    def get_valuation_metrics(self) -> Dict:
        """Get valuation metrics"""
        try:
            if self.stock is None:
                return {}
            
            info = self.stock.info
            
            return {
                'pe_ratio': info.get('trailingPE', None),
                'forward_pe': info.get('forwardPE', None),
                'pb_ratio': info.get('priceToBook', None),
                'ps_ratio': info.get('priceToSalesTrailing12Months', None),
                'peg_ratio': info.get('pegRatio', None),
                'ev_ebitda': info.get('enterpriseToEbitda', None),
                'market_cap': info.get('marketCap', None),
                'enterprise_value': info.get('enterpriseValue', None),
                'book_value': info.get('bookValue', None),
                'price_to_book': info.get('priceToBook', None)
            }
        except Exception as e:
            print(f"Error getting valuation metrics: {e}")
            return {}
    
    def get_profitability_metrics(self) -> Dict:
        """Get profitability metrics"""
        try:
            if self.stock is None:
                return {}
            
            info = self.stock.info
            
            return {
                'profit_margin': info.get('profitMargins', None),
                'operating_margin': info.get('operatingMargins', None),
                'roe': info.get('returnOnEquity', None),
                'roa': info.get('returnOnAssets', None),
                'revenue_growth': info.get('revenueGrowth', None),
                'earnings_growth': info.get('earningsGrowth', None),
                'gross_margin': info.get('grossMargins', None)
            }
        except Exception as e:
            print(f"Error getting profitability metrics: {e}")
            return {}
    
    def get_financial_health(self) -> Dict:
        """Get financial health indicators"""
        try:
            if self.stock is None:
                return {}
            
            info = self.stock.info
            
            metrics = {
                'current_ratio': info.get('currentRatio', None),
                'quick_ratio': info.get('quickRatio', None),
                'debt_to_equity': info.get('debtToEquity', None),
                'free_cash_flow': info.get('freeCashflow', None),
                'operating_cash_flow': info.get('operatingCashflow', None),
                'total_cash': info.get('totalCash', None),
                'total_debt': info.get('totalDebt', None)
            }
            
            return metrics
        except Exception as e:
            print(f"Error getting financial health: {e}")
            return {}
    
    def get_cash_flow_analysis(self) -> Dict:
        """Get comprehensive cash flow analysis"""
        try:
            if self.stock is None:
                return {'status': 'unavailable'}
            
            info = self.stock.info
            cashflow = self.stock.cashflow
            
            analysis = {
                'status': 'available',
                'operating_cash_flow': info.get('operatingCashflow', None),
                'free_cash_flow': info.get('freeCashflow', None),
                'capital_expenditure': None,
                'fcf_margin': None,
                'cash_flow_growth': None,
                'cash_to_debt': None
            }
            
            # Calculate FCF margin
            if analysis['free_cash_flow'] and info.get('totalRevenue'):
                revenue = info.get('totalRevenue')
                analysis['fcf_margin'] = (analysis['free_cash_flow'] / revenue) * 100
            
            # Calculate cash to debt ratio
            if info.get('totalCash') and info.get('totalDebt'):
                total_debt = info.get('totalDebt')
                if total_debt > 0:
                    analysis['cash_to_debt'] = info.get('totalCash') / total_debt
            
            # Get capital expenditure from cash flow statement
            if cashflow is not None and not cashflow.empty:
                if 'Capital Expenditure' in cashflow.index:
                    capex = cashflow.loc['Capital Expenditure'].iloc[0]
                    analysis['capital_expenditure'] = abs(capex) if capex else None
            
            return analysis
        except Exception as e:
            print(f"Error getting cash flow analysis: {e}")
            return {'status': 'error'}
    
    def get_management_quality(self) -> Dict:
        """Get management quality indicators"""
        try:
            if self.stock is None:
                return {'status': 'unavailable'}
            
            info = self.stock.info
            
            quality = {
                'status': 'available',
                'roe': info.get('returnOnEquity', None),
                'roa': info.get('returnOnAssets', None),
                'roic': info.get('returnOnCapital', None),
                'profit_margin': info.get('profitMargins', None),
                'operating_margin': info.get('operatingMargins', None),
                'asset_turnover': None,
                'insider_ownership': None,
                'institutional_ownership': None,
                'management_score': 0
            }
            
            # Calculate asset turnover if data available
            if info.get('totalRevenue') and info.get('totalAssets'):
                quality['asset_turnover'] = info.get('totalRevenue') / info.get('totalAssets')
            
            # Insider and institutional ownership
            quality['insider_ownership'] = info.get('heldPercentInsiders', None)
            quality['institutional_ownership'] = info.get('heldPercentInstitutions', None)
            
            # Calculate simple management quality score (0-100)
            score = 0
            if quality['roe']:
                if quality['roe'] > 0.20:
                    score += 30
                elif quality['roe'] > 0.15:
                    score += 20
                elif quality['roe'] > 0.10:
                    score += 10
            
            if quality['profit_margin']:
                if quality['profit_margin'] > 0.20:
                    score += 25
                elif quality['profit_margin'] > 0.10:
                    score += 15
                elif quality['profit_margin'] > 0.05:
                    score += 10
            
            if quality['operating_margin']:
                if quality['operating_margin'] > 0.20:
                    score += 25
                elif quality['operating_margin'] > 0.10:
                    score += 15
                elif quality['operating_margin'] > 0.05:
                    score += 10
            
            # Bonus for insider ownership
            if quality['insider_ownership']:
                if quality['insider_ownership'] > 0.10:
                    score += 20
                elif quality['insider_ownership'] > 0.05:
                    score += 10
            
            quality['management_score'] = min(score, 100)
            
            return quality
        except Exception as e:
            print(f"Error getting management quality: {e}")
            return {'status': 'error'}
    
    def get_future_outlook(self) -> Dict:
        """Get future outlook and positioning"""
        try:
            if self.stock is None:
                return {'status': 'unavailable'}
            
            info = self.stock.info
            
            outlook = {
                'status': 'available',
                'analyst_target': info.get('targetMeanPrice', None),
                'current_price': info.get('currentPrice', None),
                'upside_potential': None,
                'earnings_growth': info.get('earningsGrowth', None),
                'revenue_growth': info.get('revenueGrowth', None),
                'analyst_recommendation': info.get('recommendationKey', None),
                'num_analysts': info.get('numberOfAnalystOpinions', None),
                'esg_score': info.get('esgScores', {}).get('totalEsg', None) if isinstance(info.get('esgScores'), dict) else None,
                'industry_growth': None
            }
            
            # Calculate upside potential
            if outlook['analyst_target'] and outlook['current_price']:
                current = outlook['current_price']
                target = outlook['analyst_target']
                outlook['upside_potential'] = ((target - current) / current) * 100
            
            return outlook
        except Exception as e:
            print(f"Error getting future outlook: {e}")
            return {'status': 'error'}
    
    def get_industry_peers(self, max_peers: int = 5) -> List[str]:
        """Get industry peer companies"""
        try:
            # Hardcoded peer groups for major Indian stocks (with and without .NS)
            peer_map = {
                'RELIANCE.NS': ['TCS.NS', 'HDFCBANK.NS', 'INFY.NS', 'ICICIBANK.NS'],
                'RELIANCE': ['TCS.NS', 'HDFCBANK.NS', 'INFY.NS', 'ICICIBANK.NS'],
                'TCS.NS': ['INFY.NS', 'WIPRO.NS', 'HCLTECH.NS', 'TECHM.NS'],
                'TCS': ['INFY.NS', 'WIPRO.NS', 'HCLTECH.NS', 'TECHM.NS'],
                'INFY.NS': ['TCS.NS', 'WIPRO.NS', 'HCLTECH.NS', 'TECHM.NS'],
                'INFY': ['TCS.NS', 'WIPRO.NS', 'HCLTECH.NS', 'TECHM.NS'],
                'HDFCBANK.NS': ['ICICIBANK.NS', 'SBIN.NS', 'KOTAKBANK.NS', 'AXISBANK.NS'],
                'HDFCBANK': ['ICICIBANK.NS', 'SBIN.NS', 'KOTAKBANK.NS', 'AXISBANK.NS'],
                'ICICIBANK.NS': ['HDFCBANK.NS', 'SBIN.NS', 'KOTAKBANK.NS', 'AXISBANK.NS'],
                'ICICIBANK': ['HDFCBANK.NS', 'SBIN.NS', 'KOTAKBANK.NS', 'AXISBANK.NS'],
                'SBIN.NS': ['HDFCBANK.NS', 'ICICIBANK.NS', 'KOTAKBANK.NS', 'AXISBANK.NS'],
                'SBIN': ['HDFCBANK.NS', 'ICICIBANK.NS', 'KOTAKBANK.NS', 'AXISBANK.NS'],
                'ITC.NS': ['HINDUNILVR.NS', 'NESTLEIND.NS', 'BRITANNIA.NS', 'DABUR.NS'],
                'ITC': ['HINDUNILVR.NS', 'NESTLEIND.NS', 'BRITANNIA.NS', 'DABUR.NS'],
                'TATAMOTORS.NS': ['MARUTI.NS', 'M&M.NS', 'BAJAJ-AUTO.NS', 'HEROMOTOCO.NS'],
                'TATAMOTORS': ['MARUTI.NS', 'M&M.NS', 'BAJAJ-AUTO.NS', 'HEROMOTOCO.NS'],
                'SUNPHARMA.NS': ['DRREDDY.NS', 'CIPLA.NS', 'DIVISLAB.NS', 'AUROPHARMA.NS'],
                'SUNPHARMA': ['DRREDDY.NS', 'CIPLA.NS', 'DIVISLAB.NS', 'AUROPHARMA.NS'],
            }
            
            peers = peer_map.get(self.ticker, [])
            return peers[:max_peers]
        except Exception as e:
            print(f"Error getting peers: {e}")
            return []
    
    def compare_with_peers(self, peers: List[str]) -> pd.DataFrame:
        """Compare valuation metrics with peers"""
        try:
            comparison_data = []
            
            # Add current stock
            current_metrics = self.get_valuation_metrics()
            current_info = self.get_company_info()
            
            comparison_data.append({
                'Company': current_info['name'],
                'Ticker': self.ticker,
                'P/E': current_metrics.get('pe_ratio'),
                'P/B': current_metrics.get('pb_ratio'),
                'P/S': current_metrics.get('ps_ratio'),
                'Market Cap (Cr)': current_metrics.get('market_cap', 0) / 10000000 if current_metrics.get('market_cap') else None
            })
            
            # Add peers
            for peer in peers:
                try:
                    peer_stock = yf.Ticker(peer)
                    peer_info = peer_stock.info
                    
                    comparison_data.append({
                        'Company': peer_info.get('longName', peer_info.get('shortName', peer)),
                        'Ticker': peer,
                        'P/E': peer_info.get('trailingPE'),
                        'P/B': peer_info.get('priceToBook'),
                        'P/S': peer_info.get('priceToSalesTrailing12Months'),
                        'Market Cap (Cr)': peer_info.get('marketCap', 0) / 10000000 if peer_info.get('marketCap') else None
                    })
                except Exception as e:
                    print(f"Error getting peer {peer}: {e}")
                    continue
            
            df = pd.DataFrame(comparison_data)
            return df
        except Exception as e:
            print(f"Error comparing with peers: {e}")
            return pd.DataFrame()
    
    def get_risk_factors(self) -> Dict:
        """Get risk factors and warnings"""
        try:
            if self.stock is None:
                return {
                    'financial_risks': [],
                    'operational_risks': [],
                    'market_risks': [],
                    'regulatory_risks': []
                }
            
            info = self.stock.info
            
            risks = {
                'financial_risks': [],
                'operational_risks': [],
                'market_risks': [],
                'regulatory_risks': []
            }
            
            # Financial risks
            debt_to_equity = info.get('debtToEquity', 0)
            if debt_to_equity and debt_to_equity > 2.0:
                risks['financial_risks'].append(f"High debt-to-equity ratio: {debt_to_equity:.2f}")
            
            current_ratio = info.get('currentRatio', 0)
            if current_ratio and current_ratio < 1.0:
                risks['financial_risks'].append(f"Low current ratio: {current_ratio:.2f} (liquidity concern)")
            
            # Profitability risks
            profit_margin = info.get('profitMargins', 0)
            if profit_margin and profit_margin < 0:
                risks['operational_risks'].append("Negative profit margin (company is loss-making)")
            elif profit_margin and profit_margin < 0.05:
                risks['operational_risks'].append(f"Low profit margin: {profit_margin*100:.2f}%")
            
            # Market risks
            beta = info.get('beta', 1.0)
            if beta and beta > 1.5:
                risks['market_risks'].append(f"High volatility (Beta: {beta:.2f}) - stock moves {beta:.0f}x market")
            
            # Check for negative growth
            revenue_growth = info.get('revenueGrowth', 0)
            if revenue_growth and revenue_growth < 0:
                risks['operational_risks'].append(f"Negative revenue growth: {revenue_growth*100:.2f}%")
            
            # ESG risk
            overall_risk = info.get('overallRisk', None)
            if overall_risk and overall_risk > 7:
                risks['regulatory_risks'].append(f"High overall ESG risk score: {overall_risk}/10")
            
            return risks
        except Exception as e:
            print(f"Error getting risk factors: {e}")
            return {
                'financial_risks': [],
                'operational_risks': [],
                'market_risks': [],
                'regulatory_risks': []
            }
    
    def generate_fundamental_score(self) -> Dict:
        """
        Generate overall fundamental score (0-100)
        Based on valuation, profitability, and financial health
        """
        try:
            score = 0
            max_score = 100
            breakdown = {}
            
            # 1. Valuation Score (30 points)
            valuation = self.get_valuation_metrics()
            valuation_score = 0
            
            pe = valuation.get('pe_ratio')
            if pe:
                if pe < 15:
                    valuation_score += 15
                elif pe < 25:
                    valuation_score += 10
                elif pe < 35:
                    valuation_score += 5
            
            pb = valuation.get('pb_ratio')
            if pb:
                if pb < 2:
                    valuation_score += 15
                elif pb < 4:
                    valuation_score += 10
                elif pb < 6:
                    valuation_score += 5
            
            breakdown['valuation'] = valuation_score
            score += valuation_score
            
            # 2. Profitability Score (40 points)
            profitability = self.get_profitability_metrics()
            profit_score = 0
            
            profit_margin = profitability.get('profit_margin')
            if profit_margin:
                if profit_margin > 0.20:
                    profit_score += 15
                elif profit_margin > 0.10:
                    profit_score += 10
                elif profit_margin > 0.05:
                    profit_score += 5
            
            roe = profitability.get('roe')
            if roe:
                if roe > 0.20:
                    profit_score += 15
                elif roe > 0.15:
                    profit_score += 10
                elif roe > 0.10:
                    profit_score += 5
            
            revenue_growth = profitability.get('revenue_growth')
            if revenue_growth:
                if revenue_growth > 0.20:
                    profit_score += 10
                elif revenue_growth > 0.10:
                    profit_score += 5
            
            breakdown['profitability'] = profit_score
            score += profit_score
            
            # 3. Financial Health Score (30 points)
            health = self.get_financial_health()
            health_score = 0
            
            current_ratio = health.get('current_ratio')
            if current_ratio:
                if current_ratio > 2.0:
                    health_score += 10
                elif current_ratio > 1.5:
                    health_score += 7
                elif current_ratio > 1.0:
                    health_score += 5
            
            debt_to_equity = health.get('debt_to_equity')
            if debt_to_equity is not None:
                if debt_to_equity < 0.5:
                    health_score += 10
                elif debt_to_equity < 1.0:
                    health_score += 7
                elif debt_to_equity < 2.0:
                    health_score += 3
            
            fcf = health.get('free_cash_flow')
            if fcf and fcf > 0:
                health_score += 10
            
            breakdown['health'] = health_score
            score += health_score
            
            # Overall rating
            if score >= 80:
                rating = "Excellent"
                color = "#48bb78"
            elif score >= 60:
                rating = "Good"
                color = "#667eea"
            elif score >= 40:
                rating = "Average"
                color = "#ed8936"
            elif score >= 20:
                rating = "Below Average"
                color = "#f56565"
            else:
                rating = "Poor"
                color = "#c53030"
            
            return {
                'score': score,
                'max_score': max_score,
                'rating': rating,
                'color': color,
                'breakdown': breakdown
            }
        except Exception as e:
            print(f"Error generating fundamental score: {e}")
            return {
                'score': 0,
                'max_score': 100,
                'rating': 'Unavailable',
                'color': '#999',
                'breakdown': {}
            }


# Helper function for formatting
def format_large_number(num):
    """Format large numbers (Cr, L, K)"""
    if num is None or pd.isna(num):
        return "N/A"
    
    if num >= 10000000:  # 1 Crore
        return f"₹{num/10000000:.2f} Cr"
    elif num >= 100000:  # 1 Lakh
        return f"₹{num/100000:.2f} L"
    elif num >= 1000:
        return f"₹{num/1000:.2f} K"
    else:
        return f"₹{num:.2f}"


def format_percentage(value, decimals=2):
    """Format percentage"""
    if value is None or pd.isna(value):
        return "N/A"
    return f"{value*100:.{decimals}f}%"

