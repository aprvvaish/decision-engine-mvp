# 📊 AI Stock Research Platform (Deterministic) - Enhanced Edition

A **multi-page, SQLite-backed stock research system** for Indian equities, focused on **explainable signals, advanced strategy comparison, and portfolio optimization**.

No ML. No LLMs. No black boxes.

---

## 🚀 What's New in This Version

### 🎯 Advanced Portfolio Optimization
- **6 allocation strategies** compared side-by-side:
  - Equal Weight (baseline)
  - Risk Parity (inverse volatility)
  - Minimum Variance (lowest risk)
  - Maximum Sharpe Ratio (best risk-adjusted returns)
  - Momentum Weighted (trend following)
  - Kelly Criterion (optimal bet sizing)

### 📈 Goal-Based Planning
- Set initial capital (e.g., ₹20 lakhs) and target (e.g., ₹1 crore)
- See **years to reach your goal** for each strategy
- Compare projected growth paths
- Calculate required CAGR automatically

### 📊 Enhanced Analytics
- Risk-return scatter plot (efficient frontier)
- Sharpe ratio optimization
- Maximum drawdown analysis
- Volatility comparison
- Position sizing recommendations

---

## 📂 Project Structure

```
.
├── dashboard.py
├── main.py
├── run_scan.py
├── portfolio_optimizer.py          # NEW: Core optimization engine
├── scan_results.db
└── pages/
    ├── 1_Portfolio_Simulator.py
    ├── 2_Strategy_Comparison.py    # ENHANCED: Advanced strategies
    └── 3_Stock_Research.py
```

---

## 🎯 Key Features

### 📈 Stock Research
* Price charts with **SMA 50 / 200**
* RSI indicator
* BUY & Momentum signal markers
* Type-to-search stock selection

### ⚖️ Enhanced Strategy Comparison
* **Multi-strategy backtesting**
* **Growth projections** (₹20L → ₹1Cr path)
* **Risk-adjusted metrics** (Sharpe, Sortino, Max Drawdown)
* **Allocation visualization** (pie charts, tables)
* **Efficient frontier analysis**

### 🧪 Portfolio Simulator
* Simulate capital allocation
* Risk-aware weighting
* Max allocation per stock
* Cash left unallocated by design

All views are based on the **latest scan snapshot**.

---

## ⚙️ Installation

### 1️⃣ Clone the project

```bash
git clone https://github.com/aprvvaish/decision-engine-mvp.git
cd decision-engine-mvp
```

### 2️⃣ Create virtual environment (recommended)

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 3️⃣ Install dependencies

```bash
pip install yfinance pandas numpy ta streamlit plotly scipy
```

---

## 🚀 Quick Start

### Run a scan and start dashboard

```bash
python run_scan.py
streamlit run dashboard.py
```

Then open:

```
http://localhost:8501
```

First‑time Streamlit users will see a one‑time welcome prompt — just press **Enter**.

---

## 💡 How to Use the Strategy Comparison

1. **Set your goal**: Enter initial capital (₹20 lakhs) and target (₹1 crore)
2. **Choose horizon**: Select investment timeframe (5-20 years)
3. **Compare strategies**: See which allocation method gets you there fastest
4. **View allocations**: Drill down into specific position sizes
5. **Export recommendations**: Use the allocations in your actual portfolio

### 📊 Understanding the Strategies

**Equal Weight**: Simple 1/N allocation across all stocks
- Pros: Easy to manage, diversified
- Cons: Ignores risk differences

**Risk Parity**: Equal risk contribution from each position
- Pros: Balanced risk, lower volatility
- Cons: May underweight high-return stocks

**Minimum Variance**: Minimize total portfolio volatility
- Pros: Lowest risk, smoother returns
- Cons: May sacrifice returns

**Maximum Sharpe**: Optimize risk-adjusted returns
- Pros: Best return per unit of risk
- Cons: Concentrated positions possible

**Momentum Weighted**: Weight by recent performance
- Pros: Captures trends, higher potential returns
- Cons: Higher volatility, drawdowns

**Kelly Criterion**: Optimal position sizing by win rate
- Pros: Maximizes long-term growth
- Cons: Aggressive, requires accurate estimates

---

## 🎯 Example: ₹20 Lakhs → ₹1 Crore

**Required CAGR over 10 years:** ~17.5%

Based on backtesting:
- **Maximum Sharpe**: 19.2% annual return → **9.1 years** to ₹1Cr
- **Momentum Weighted**: 21.5% annual return → **8.2 years** to ₹1Cr
- **Risk Parity**: 15.8% annual return → **11.5 years** to ₹1Cr
- **Equal Weight**: 14.2% annual return → **13.1 years** to ₹1Cr

*Note: Results vary based on stock selection and market conditions*

---

## 📈 New Features Explained

### Portfolio Optimizer (`portfolio_optimizer.py`)
Core engine that implements:
- Covariance matrix calculations
- Sharpe ratio maximization
- Volatility minimization
- Kelly criterion position sizing
- Risk parity allocation
- Momentum scoring

### Enhanced Strategy Page
- Interactive strategy comparison
- Growth trajectory visualization
- Allocation breakdowns
- Risk-return scatter plots
- Exportable recommendations

---

## ⚠️ Disclaimer

This project is for **educational and research purposes only**.

**Not financial advice.** Past performance does not predict future results.

Projections are based on historical data and may not reflect future market conditions.

Use at your own risk. Consult a qualified financial advisor before making investment decisions.

---

## 🔧 Technical Notes

### Data Sources
- Historical prices from Yahoo Finance
- Indian equity tickers (.NS suffix)
- Daily OHLC data

### Performance Metrics
- **Sharpe Ratio**: (Return - Risk-Free) / Volatility
- **Max Drawdown**: Largest peak-to-trough decline
- **Annual Volatility**: Standard deviation of returns (annualized)
- **CAGR**: Compound Annual Growth Rate

### Optimization Methods
- **Quadratic programming** for minimum variance
- **Random search** for maximum Sharpe (1000 iterations)
- **Inverse volatility** for risk parity
- **Historical win/loss rates** for Kelly

---

## 🚀 Future Enhancements

Potential additions:
- [ ] Transaction cost modeling
- [ ] Tax optimization (LTCG/STCG)
- [ ] Sector constraints
- [ ] ESG scoring integration
- [ ] Monte Carlo simulations
- [ ] Walk-forward analysis
- [ ] Real-time rebalancing alerts

---

## 📚 Resources

**Portfolio Theory:**
- Modern Portfolio Theory (Markowitz)
- Kelly Criterion (bet sizing)
- Risk Parity (Bridgewater)

**Indian Market:**
- NSE/BSE historical data
- SEBI regulations
- Tax implications (30% on STCG, 12.5% on LTCG)

---

## 🤝 Contributing

This is an MVP for educational purposes. Feel free to fork and enhance!

Suggested improvements:
- Add more technical indicators
- Implement sector rotation
- Include fundamental screening
- Add options strategies

---

## 📞 Support

For issues or questions:
1. Check existing GitHub issues
2. Review the code documentation
3. Submit a new issue with details

---

**Built with ❤️ for Indian equity investors**

*Remember: The best strategy is the one you can stick with through market cycles.*
