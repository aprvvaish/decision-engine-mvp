import pandas as pd
import numpy as np
import yfinance as yf

# =====================================================
# PRICE DATA
# =====================================================
def fetch_data(symbol, period="3y", start=None):
    if start is not None:
        df = yf.download(symbol, start=start, progress=False)
    else:
        df = yf.download(symbol, period=period, progress=False)

    if df is None or df.shape[0] == 0:
        raise RuntimeError(f"No price data for {symbol}")

    return df


# =====================================================
# TECHNICAL INDICATORS
# =====================================================
def compute_indicators(df):
    df = df.copy()

    df["SMA_50"] = df["Close"].rolling(50).mean()
    df["SMA_200"] = df["Close"].rolling(200).mean()

    delta = df["Close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()

    rs = avg_gain / avg_loss
    df["RSI"] = 100 - (100 / (1 + rs))

    return df


# =====================================================
# SIGNALS
# =====================================================
def buy_signal_from_row(row):
    if pd.isna(row["SMA_200"]) or pd.isna(row["RSI"]):
        return "HOLD"
    return "BUY" if (row["Close"] > row["SMA_200"] and row["RSI"] < 40) else "HOLD"


def momentum_signal_from_row(row):
    if (
        pd.isna(row["SMA_50"])
        or pd.isna(row["SMA_200"])
        or pd.isna(row["RSI"])
    ):
        return "HOLD"
    return "BUY" if (row["SMA_50"] > row["SMA_200"] and row["RSI"] > 50) else "HOLD"


# =====================================================
# FUNDAMENTALS
# =====================================================
def fetch_fundamentals(symbol):
    try:
        info = yf.Ticker(symbol).info or {}

        roe = info.get("returnOnEquity", None)
        roce = info.get("returnOnCapitalEmployed", None)

        return {
            "roe": round(roe * 100, 2) if roe is not None and not pd.isna(roe) else None,
            "roce": round(roce * 100, 2) if roce is not None and not pd.isna(roce) else None,
        }
    except Exception:
        return {"roe": None, "roce": None}


# =====================================================
# CONSERVATIVE DCF
# =====================================================
def conservative_dcf(symbol, price):
    try:
        info = yf.Ticker(symbol).info or {}

        fcf = info.get("freeCashflow", None)
        shares = info.get("sharesOutstanding", None)
        roce = info.get("returnOnCapitalEmployed", None)

        if fcf is None or shares is None or pd.isna(fcf) or pd.isna(shares):
            return None

        growth = min((roce if roce and not pd.isna(roce) else 0.06) * 100, 12)

        discount_rate = 0.12
        terminal_growth = 0.04
        years = 5

        cashflows = []
        for i in range(1, years + 1):
            fcf *= (1 + growth / 100)
            cashflows.append(fcf / ((1 + discount_rate) ** i))

        terminal_value = (
            cashflows[-1] * (1 + terminal_growth)
        ) / (discount_rate - terminal_growth)

        terminal_discounted = terminal_value / ((1 + discount_rate) ** years)
        intrinsic_equity = sum(cashflows) + terminal_discounted
        intrinsic_per_share = intrinsic_equity / shares

        mos = (intrinsic_per_share - price) / price * 100

        return {
            "intrinsic_value": round(intrinsic_per_share, 2),
            "margin_of_safety_pct": round(mos, 1),
            "growth_assumption_pct": round(growth, 1),
        }

    except Exception:
        return None


# =====================================================
# PORTFOLIO EQUITY ENGINE
# =====================================================
def build_portfolio_equity_curve(
    tickers,
    weights,
    initial_capital,
    start_date
):
    frames = []

    for t in tickers:
        try:
            df = fetch_data(t, start=start_date)[["Close"]]
            frames.append(df.rename(columns={"Close": t}))
        except Exception:
            continue

    if len(frames) == 0:
        raise RuntimeError("No usable price data")

    prices = pd.concat(frames, axis=1)
    prices = prices.dropna()

    if prices.shape[0] == 0:
        raise RuntimeError("Price data empty after alignment")

    norm = prices / prices.iloc[0]

    equity = pd.Series(0.0, index=norm.index)

    for t in norm.columns:
        w = weights.get(t, 0.0)
        if isinstance(w, (int, float)) and w > 0:
            equity = equity.add(norm[t] * (initial_capital * w), fill_value=0)

    cash_weight = 1.0 - float(sum(weights.values()))
    if cash_weight > 0:
        equity = equity + (initial_capital * cash_weight)

    rolling_max = equity.cummax()
    drawdown = (equity - rolling_max) / rolling_max

    if drawdown.isna().all():
        return {
            "equity_curve": equity,
            "drawdown": drawdown,
            "max_drawdown_pct": 0.0,
            "max_drawdown_date": None,
            "recovery_date": None,
        }

    min_dd = drawdown.min()

    if pd.isna(min_dd) or min_dd >= 0:
        max_dd_pct = 0.0
        max_dd_date = None
        recovery_date = None
    else:
        max_dd_pct = round(min_dd * 100, 2)
        max_dd_date = drawdown.idxmin()

        peak_value = rolling_max.loc[max_dd_date]
        after_dd = equity.loc[max_dd_date:]
        recovered = after_dd[after_dd >= peak_value]
        recovery_date = recovered.index[0] if recovered.shape[0] > 0 else None

    return {
        "equity_curve": equity,
        "drawdown": drawdown,
        "max_drawdown_pct": max_dd_pct,
        "max_drawdown_date": max_dd_date,
        "recovery_date": recovery_date,
    }
