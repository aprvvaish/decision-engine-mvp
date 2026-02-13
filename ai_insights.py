"""
AI Insights Generator
Generates automated insights for portfolios and stocks using LLM
"""

import streamlit as st
import pandas as pd
import json
from typing import Dict, List, Optional

class AIInsightsGenerator:
    """
    Generate AI-powered insights for portfolios and stocks
    
    Usage:
        insights = AIInsightsGenerator()
        result = insights.analyze_portfolio(portfolio_data)
        st.info(result)
    """
    
    def __init__(self, use_ollama=True):
        """
        Initialize insights generator
        
        Args:
            use_ollama: If True, use Ollama (default). If False, use Claude API
        """
        self.use_ollama = use_ollama
        
        if not use_ollama:
            # Claude API (optional, costs money)
            try:
                import anthropic
                self.client = anthropic.Anthropic(
                    api_key=st.secrets["anthropic"]["api_key"]
                )
            except:
                st.warning("Claude API not configured. Using Ollama instead.")
                self.use_ollama = True
                self.client = None
        
        if self.use_ollama:
            # Ollama (free, local)
            try:
                import ollama
                self.ollama = ollama
                # Test connection
                try:
                    ollama.list()
                except:
                    st.warning("Ollama not running. Start it with: ollama serve")
            except ImportError:
                st.error("Ollama not installed. Install: pip install ollama")
                self.ollama = None
    
    def _call_llm(self, prompt: str, max_tokens: int = 512) -> str:
        """Call LLM with prompt"""
        
        if self.use_ollama and self.ollama:
            # Use Ollama (free, local)
            try:
                response = self.ollama.chat(
                    model='llama3.1',
                    messages=[
                        {
                            'role': 'system',
                            'content': 'You are a financial analysis assistant for Indian stock markets. Be concise, specific, and actionable.'
                        },
                        {
                            'role': 'user',
                            'content': prompt
                        }
                    ]
                )
                return response['message']['content']
            except Exception as e:
                return f"Error calling Ollama: {str(e)}\n\nMake sure Ollama is running (ollama serve) and llama3.1 is installed (ollama pull llama3.1)."
        
        elif not self.use_ollama and self.client:
            # Use Claude API (costs money)
            try:
                message = self.client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=max_tokens,
                    messages=[{"role": "user", "content": prompt}]
                )
                return message.content[0].text
            except Exception as e:
                return f"Error calling Claude API: {str(e)}"
        
        else:
            return "LLM not available. Install Ollama: https://ollama.com/download"
    
    def analyze_portfolio(self, performance_data: Dict) -> str:
        """
        Generate portfolio analysis insights
        
        Args:
            performance_data: Dict with portfolio performance data
        
        Returns:
            Formatted insights text
        """
        
        prompt = f"""Analyze this portfolio and provide 3 concise insights:

Portfolio: {performance_data.get('portfolio_name', 'Unknown')}
Initial Capital: ₹{performance_data.get('initial_capital', 0):,}
Current Value: ₹{performance_data.get('total_value', 0):,}
Gain/Loss: {performance_data.get('total_gain_pct', 0):.2f}%

Top 3 positions by gain:
{self._format_top_positions(performance_data.get('positions', []))}

Provide:
1. Overall performance assessment (1 sentence)
2. Key driver of performance (1 sentence)  
3. One actionable recommendation (1 sentence)

Format as numbered list. Be specific with numbers."""

        return self._call_llm(prompt, max_tokens=512)
    
    def _format_top_positions(self, positions: List[Dict], top_n: int = 3) -> str:
        """Format top positions for prompt"""
        if not positions:
            return "No positions"
        
        sorted_positions = sorted(
            positions, 
            key=lambda x: x.get('gain_loss_pct', 0), 
            reverse=True
        )
        
        result = []
        for i, pos in enumerate(sorted_positions[:top_n], 1):
            ticker = pos.get('ticker', 'Unknown')
            gain_pct = pos.get('gain_loss_pct', 0)
            result.append(f"{i}. {ticker}: {gain_pct:+.2f}%")
        
        return "\n".join(result)
    
    def compare_portfolios(self, portfolio1: Dict, portfolio2: Dict) -> str:
        """
        Compare two portfolios
        
        Args:
            portfolio1: First portfolio performance data
            portfolio2: Second portfolio performance data
        
        Returns:
            Comparison insights
        """
        
        prompt = f"""Compare these two portfolios and recommend which one to use:

Portfolio A: {portfolio1.get('portfolio_name')}
- Return: {portfolio1.get('total_gain_pct', 0):.2f}%
- Current Value: ₹{portfolio1.get('total_value', 0):,}
- Strategy: {portfolio1.get('strategy', 'Unknown')}

Portfolio B: {portfolio2.get('portfolio_name')}
- Return: {portfolio2.get('total_gain_pct', 0):.2f}%
- Current Value: ₹{portfolio2.get('total_value', 0):,}
- Strategy: {portfolio2.get('strategy', 'Unknown')}

Provide:
1. Which performed better and by how much
2. Why it performed better (1 reason)
3. Which to choose for ₹20L → ₹1Cr goal

Be concise (3-4 sentences total)."""

        return self._call_llm(prompt, max_tokens=384)
    
    def generate_stock_insight(self, stock_data: Dict) -> str:
        """
        Generate insight for a single stock
        
        Args:
            stock_data: Dict with stock technical data
        
        Returns:
            Stock insight text
        """
        
        ticker = stock_data.get('ticker', 'Unknown')
        price = stock_data.get('close_price', 0)
        rsi = stock_data.get('rsi', 50)
        sma_50 = stock_data.get('sma_50', 0)
        sma_200 = stock_data.get('sma_200', 0)
        
        # Determine trend
        if price > sma_50 > sma_200:
            trend = "Strong uptrend"
        elif price > sma_50:
            trend = "Uptrend"
        elif price < sma_50 < sma_200:
            trend = "Strong downtrend"
        else:
            trend = "Downtrend"
        
        prompt = f"""Provide 2-sentence insight on this stock:

{ticker}
- Current Price: ₹{price:.2f}
- RSI: {rsi:.1f}
- Trend: {trend}
- Price vs SMA50: {"Above" if price > sma_50 else "Below"}

Give:
1. One observation about current state
2. One suggestion (hold/buy/wait)

Be specific and actionable."""

        return self._call_llm(prompt, max_tokens=256)
    
    def explain_strategy(self, strategy_name: str) -> str:
        """
        Explain an investment strategy in simple terms
        
        Args:
            strategy_name: Name of strategy (e.g., "Maximum Sharpe")
        
        Returns:
            Explanation text
        """
        
        prompt = f"""Explain the "{strategy_name}" portfolio strategy in simple terms:

1. What it is (1 sentence)
2. How it works (2 sentences)
3. Best use case (1 sentence)
4. Main advantage (1 sentence)

Use simple language. No jargon. Target: beginner investor."""

        return self._call_llm(prompt, max_tokens=512)
    
    def generate_alert_message(self, alert_type: str, alert_data: Dict) -> str:
        """
        Generate natural language alert message
        
        Args:
            alert_type: Type of alert (concentration, loss, gain, etc.)
            alert_data: Alert-specific data
        
        Returns:
            Alert message
        """
        
        prompts = {
            'concentration': f"""Portfolio alert - position too large:

Stock: {alert_data.get('stock')}
Current weight: {alert_data.get('weight', 0)*100:.1f}%
Recommended max: 10%

Write 2-sentence alert:
1. Explain the risk
2. Suggest action

Be direct and specific.""",

            'loss': f"""Portfolio alert - significant loss:

Stock: {alert_data.get('stock')}
Loss: {alert_data.get('loss', 0):.2f}%

Write 2-sentence alert:
1. State the loss
2. Suggest next step (review/hold/cut)

Be supportive, not alarmist.""",

            'gain': f"""Portfolio alert - significant gain:

Stock: {alert_data.get('stock')}
Gain: {alert_data.get('gain', 0):.2f}%

Write 2-sentence alert:
1. Celebrate the gain
2. Suggest action (hold/partial profit)

Be positive but prudent.""",

            'rebalance': f"""Portfolio alert - rebalancing needed:

Out of balance positions: {alert_data.get('count', 0)}
Largest drift: {alert_data.get('max_drift', 0):.1f}%

Write 2-sentence alert:
1. Explain why rebalance is needed
2. Suggest when to do it

Be practical."""
        }
        
        prompt = prompts.get(alert_type, "Generate a generic alert message.")
        
        return self._call_llm(prompt, max_tokens=256)
    
    def generate_report(self, portfolio_data: Dict, include_recommendations: bool = True) -> str:
        """
        Generate comprehensive portfolio report
        
        Args:
            portfolio_data: Complete portfolio data
            include_recommendations: Whether to include actionable recommendations
        
        Returns:
            Formatted report text
        """
        
        prompt = f"""Generate a portfolio analysis report:

PORTFOLIO: {portfolio_data.get('portfolio_name')}

PERFORMANCE:
- Initial: ₹{portfolio_data.get('initial_capital', 0):,}
- Current: ₹{portfolio_data.get('total_value', 0):,}
- Gain/Loss: {portfolio_data.get('total_gain_pct', 0):.2f}%

TOP PERFORMERS:
{self._format_top_positions(portfolio_data.get('positions', []), top_n=3)}

BOTTOM PERFORMERS:
{self._format_bottom_positions(portfolio_data.get('positions', []), top_n=2)}

Generate report with:
1. Executive Summary (2 sentences)
2. Performance Highlights (3 bullet points)
3. Risk Assessment (2 sentences)
{f"4. Recommendations (3 actionable items)" if include_recommendations else ""}

Use clear headings. Be professional but accessible."""

        return self._call_llm(prompt, max_tokens=1024)
    
    def _format_bottom_positions(self, positions: List[Dict], top_n: int = 2) -> str:
        """Format bottom positions for prompt"""
        if not positions:
            return "No positions"
        
        sorted_positions = sorted(
            positions,
            key=lambda x: x.get('gain_loss_pct', 0)
        )
        
        result = []
        for i, pos in enumerate(sorted_positions[:top_n], 1):
            ticker = pos.get('ticker', 'Unknown')
            gain_pct = pos.get('gain_loss_pct', 0)
            result.append(f"{i}. {ticker}: {gain_pct:+.2f}%")
        
        return "\n".join(result)
    
    def answer_question(self, question: str, context: Dict) -> str:
        """
        Answer a general question about portfolio/stocks
        
        Args:
            question: User's question
            context: Relevant context data
        
        Returns:
            Answer text
        """
        
        prompt = f"""Answer this question about the portfolio/stocks:

Question: {question}

Available context:
{json.dumps(context, indent=2)}

Provide a clear, concise answer (2-3 sentences).
Be specific, cite data when relevant."""

        return self._call_llm(prompt, max_tokens=512)


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

@st.cache_data(ttl=300, show_spinner=False)
def get_portfolio_insights(portfolio_name: str, performance_data: Dict) -> str:
    """
    Cached function to get portfolio insights using Ollama
    
    Usage in Streamlit pages:
        insights = get_portfolio_insights("My Portfolio", performance_data)
        st.info(insights)
    """
    generator = AIInsightsGenerator(use_ollama=True)
    return generator.analyze_portfolio(performance_data)


@st.cache_data(ttl=300, show_spinner=False)
def compare_portfolio_performance(portfolio1: Dict, portfolio2: Dict) -> str:
    """
    Cached function to compare portfolios using Ollama
    
    Usage:
        comparison = compare_portfolio_performance(perf1, perf2)
        st.write(comparison)
    """
    generator = AIInsightsGenerator(use_ollama=True)
    return generator.compare_portfolios(portfolio1, portfolio2)


@st.cache_data(ttl=600, show_spinner=False)
def explain_investment_strategy(strategy_name: str) -> str:
    """
    Cached function to explain strategies using Ollama
    
    Usage:
        explanation = explain_investment_strategy("Maximum Sharpe")
        st.info(explanation)
    """
    generator = AIInsightsGenerator(use_ollama=True)
    return generator.explain_strategy(strategy_name)


def generate_smart_alert(alert_type: str, alert_data: Dict) -> str:
    """
    Generate smart alert message using Ollama
    
    Usage:
        alert = generate_smart_alert('loss', {'stock': 'TCS', 'loss': -5.2})
        st.warning(alert)
    """
    generator = AIInsightsGenerator(use_ollama=True)
    return generator.generate_alert_message(alert_type, alert_data)


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    # Example: Generate portfolio insights
    sample_performance = {
        'portfolio_name': 'Aggressive Growth',
        'initial_capital': 2000000,
        'total_value': 2120000,
        'total_gain_pct': 6.0,
        'positions': [
            {'ticker': 'TCS', 'gain_loss_pct': 12.0},
            {'ticker': 'INFY', 'gain_loss_pct': 8.5},
            {'ticker': 'RELIANCE', 'gain_loss_pct': 4.2},
            {'ticker': 'TATAMOTORS', 'gain_loss_pct': -3.3}
        ]
    }
    
    generator = AIInsightsGenerator()
    insights = generator.analyze_portfolio(sample_performance)
    print("Portfolio Insights:")
    print(insights)
    print("\n" + "="*50 + "\n")
    
    # Example: Compare portfolios
    portfolio1 = {
        'portfolio_name': 'Aggressive',
        'total_gain_pct': 6.0,
        'total_value': 2120000,
        'strategy': 'Momentum'
    }
    
    portfolio2 = {
        'portfolio_name': 'Conservative',
        'total_gain_pct': 3.2,
        'total_value': 2064000,
        'strategy': 'Risk Parity'
    }
    
    comparison = generator.compare_portfolios(portfolio1, portfolio2)
    print("Portfolio Comparison:")
    print(comparison)
    print("\n" + "="*50 + "\n")
    
    # Example: Generate alert
    alert = generator.generate_alert_message(
        'concentration',
        {'stock': 'RELIANCE', 'weight': 0.15}
    )
    print("Smart Alert:")
    print(alert)
