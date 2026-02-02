# 📊 AI Stock Research Platform (Deterministic)

A **multi-page, SQLite-backed stock research system** for Indian equities, focused on **explainable signals, strategy comparison, and portfolio simulation**.

No ML. No LLMs. No black boxes.

---

## 🚀 What This Does

### 📈 Stock Research
- Price charts with **SMA 50 / 200**
- RSI indicator
- BUY & Momentum signal markers
- Type-to-search stock selection

### ⚖️ Strategy Comparison
- BUY vs Momentum strategies
- Backtested metrics:
  - Sharpe ratio
  - Total return
  - Max drawdown
- Market-regime insight

### 🧪 Portfolio Simulator
- Simulate capital allocation
- Risk-aware weighting
- Max allocation per stock
- Cash left unallocated by design

All views are based on the **latest scan snapshot**.

---
## 📂 Project Structure

```
.
├── dashboard.py
├── main.py
├── run_scan.py
├── scan_results.db
└── pages/
├── 1_Portfolio_Simulator.py
├── 2_Strategy_Comparison.py
└── 3_Stock_Research.py
```

---

## ⚙️ Installation

### 1️⃣ Clone / copy the project

```bash
git clone <repo-url>
cd ai-stock-analysis
```

### 2️⃣ Create virtual environment (recommended)

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 3️⃣ Install dependencies

```bash
pip install yfinance pandas numpy ta streamlit
```

---
## Run a scan and start dashboard
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

## ⚠️ Disclaimer

This project is for **educational and research purposes only**.
Not financial advice. Past performance does not predict future results.

Use at your own risk.

---


