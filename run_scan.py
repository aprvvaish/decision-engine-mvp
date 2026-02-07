"""
Enhanced Stock Scanner for Indian Equities
Scans stocks, calculates technical indicators, and stores in SQLite database
"""

import yfinance as yf
import pandas as pd
import numpy as np
import sqlite3
from datetime import datetime, timedelta
import ta
import warnings
warnings.filterwarnings('ignore')

# Indian stock universe (NSE-listed)
STOCK_UNIVERSE = [
    # Large Cap - IT
    'TCS.NS', 'INFY.NS', 'HCLTECH.NS', 'WIPRO.NS', 'TECHM.NS',
    
    # Large Cap - Banking/Finance
    'HDFCBANK.NS', 'ICICIBANK.NS', 'SBIN.NS', 'KOTAKBANK.NS', 'AXISBANK.NS',
    
    # Large Cap - Energy/Oil
    'RELIANCE.NS', 'ONGC.NS', 'BPCL.NS', 'IOC.NS',
    
    # Large Cap - Automotive
    'MARUTI.NS', 'TATAMOTORS.NS', 'M&M.NS', 'BAJAJ-AUTO.NS',
    
    # Large Cap - FMCG/Consumer
    'HINDUNILVR.NS', 'ITC.NS', 'NESTLEIND.NS', 'BRITANNIA.NS',
    
    # Large Cap - Pharma
    'SUNPHARMA.NS', 'DRREDDY.NS', 'CIPLA.NS', 'DIVISLAB.NS',
    
    # Mid Cap
    'ADANIENT.NS', 'LT.NS', 'TITAN.NS', 'BAJFINANCE.NS', 'ASIANPAINT.NS'
]

# Scanner configuration
LOOKBACK_DAYS = 365  # 1 year of historical data
FETCH_TIMEOUT = 3   # Timeout in seconds for each stock (increase if network is slow)
DB_PATH = "scan_results.db"

def fetch_stock_data(ticker, days=LOOKBACK_DAYS):
    """
    Fetch historical stock data from Yahoo Finance with timeout
    
    Args:
        ticker: Stock ticker symbol (e.g., 'TCS.NS')
        days: Number of days of historical data
        
    Returns:
        DataFrame with OHLCV data
    """
    import threading
    
    result = {'data': None, 'error': None}
    
    def fetch_with_timeout():
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            stock = yf.Ticker(ticker)
            # Use timeout in download
            df = stock.history(start=start_date, end=end_date, timeout=FETCH_TIMEOUT)
            
            if df.empty:
                result['error'] = "No data returned"
                return
            
            # Rename columns to match expected format
            df = df.rename(columns={
                'Open': 'open',
                'High': 'high',
                'Low': 'low',
                'Close': 'close',
                'Volume': 'volume'
            })
            
            df['ticker'] = ticker.replace('.NS', '')  # Clean ticker
            result['data'] = df
            
        except Exception as e:
            result['error'] = str(e)
    
    print(f"  Fetching {ticker}...", end=" ", flush=True)
    
    # Run fetch in thread with timeout
    thread = threading.Thread(target=fetch_with_timeout)
    thread.daemon = True
    thread.start()
    thread.join(timeout=FETCH_TIMEOUT + 2)  # Add 2 seconds buffer
    
    if thread.is_alive():
        print("❌ Timeout")
        return None
    
    if result['error']:
        print(f"❌ {result['error']}")
        return None
    
    if result['data'] is not None and not result['data'].empty:
        print(f"✓ {len(result['data'])} days")
        return result['data']
    
    print("❌ No data")
    return None

def calculate_indicators(df):
    """
    Calculate technical indicators
    
    Args:
        df: DataFrame with OHLCV data
        
    Returns:
        DataFrame with added indicators
    """
    # Simple Moving Averages
    df['sma_50'] = ta.trend.sma_indicator(df['close'], window=50)
    df['sma_200'] = ta.trend.sma_indicator(df['close'], window=200)
    
    # RSI
    df['rsi'] = ta.momentum.rsi(df['close'], window=14)
    
    # MACD
    macd = ta.trend.MACD(df['close'])
    df['macd'] = macd.macd()
    df['macd_signal'] = macd.macd_signal()
    
    # Bollinger Bands
    bollinger = ta.volatility.BollingerBands(df['close'])
    df['bb_upper'] = bollinger.bollinger_hband()
    df['bb_lower'] = bollinger.bollinger_lband()
    df['bb_middle'] = bollinger.bollinger_mavg()
    
    # Volume SMA
    df['volume_sma'] = ta.trend.sma_indicator(df['volume'], window=20)
    
    return df

def generate_signals(df):
    """
    Generate BUY and Momentum signals
    
    Args:
        df: DataFrame with indicators
        
    Returns:
        DataFrame with signal columns
    """
    # Initialize signals
    df['buy_signal'] = False
    df['momentum_signal'] = False
    
    # BUY Signal: Golden Cross + RSI oversold recovery
    golden_cross = (df['sma_50'] > df['sma_200']) & \
                   (df['sma_50'].shift(1) <= df['sma_200'].shift(1))
    rsi_recovery = (df['rsi'] > 30) & (df['rsi'].shift(1) <= 30)
    
    df.loc[golden_cross | rsi_recovery, 'buy_signal'] = True
    
    # Momentum Signal: Strong uptrend + volume confirmation
    price_momentum = (df['close'] > df['sma_50']) & \
                     (df['sma_50'] > df['sma_200']) & \
                     (df['close'] > df['close'].shift(5))  # Price rising over 5 days
    
    volume_confirmation = df['volume'] > df['volume_sma']
    
    macd_bullish = df['macd'] > df['macd_signal']
    
    df.loc[price_momentum & volume_confirmation & macd_bullish, 'momentum_signal'] = True
    
    return df

def create_database():
    """
    Create SQLite database and table if not exists
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS scan_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            date TEXT NOT NULL,
            open_price REAL,
            high_price REAL,
            low_price REAL,
            close_price REAL,
            volume INTEGER,
            sma_50 REAL,
            sma_200 REAL,
            rsi REAL,
            macd REAL,
            macd_signal REAL,
            bb_upper REAL,
            bb_lower REAL,
            bb_middle REAL,
            buy_signal INTEGER,
            momentum_signal INTEGER,
            scan_timestamp TEXT,
            UNIQUE(ticker, date)
        )
    ''')
    
    # Create index for faster queries
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_ticker_date 
        ON scan_results(ticker, date)
    ''')
    
    conn.commit()
    conn.close()
    
    print("✓ Database initialized")

def save_to_database(df, ticker):
    """
    Save scan results to database
    
    Args:
        df: DataFrame with scan results
        ticker: Stock ticker
    """
    if df is None or df.empty:
        return
    
    conn = sqlite3.connect(DB_PATH)
    
    # Prepare data for insertion
    df_to_save = df.copy()
    df_to_save['date'] = df_to_save.index.strftime('%Y-%m-%d')
    df_to_save['scan_timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Convert boolean signals to integers
    df_to_save['buy_signal'] = df_to_save['buy_signal'].astype(int)
    df_to_save['momentum_signal'] = df_to_save['momentum_signal'].astype(int)
    
    # Rename columns to match database schema
    df_to_save = df_to_save.rename(columns={
        'open': 'open_price',
        'high': 'high_price',
        'low': 'low_price',
        'close': 'close_price'
    })
    
    # Select only required columns
    columns_to_save = [
        'ticker', 'date', 'open_price', 'high_price', 'low_price', 
        'close_price', 'volume', 'sma_50', 'sma_200', 'rsi',
        'macd', 'macd_signal', 'bb_upper', 'bb_lower', 'bb_middle',
        'buy_signal', 'momentum_signal', 'scan_timestamp'
    ]
    
    df_to_save = df_to_save[columns_to_save]
    
    # Delete existing data for this ticker (to avoid duplicates)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM scan_results WHERE ticker = ?", (ticker.replace('.NS', ''),))
    
    # Insert new data
    df_to_save.to_sql('scan_results', conn, if_exists='append', index=False)
    
    conn.commit()
    conn.close()

def print_summary(ticker, df):
    """
    Print summary of scan results
    
    Args:
        ticker: Stock ticker
        df: DataFrame with scan results
    """
    if df is None or df.empty:
        return
    
    latest = df.iloc[-1]
    
    # Count signals in last 30 days
    recent = df.tail(30)
    buy_count = recent['buy_signal'].sum()
    momentum_count = recent['momentum_signal'].sum()
    
    print(f"\n  📊 {ticker}")
    print(f"     Latest Close: ₹{latest['close']:.2f}")
    print(f"     SMA 50: ₹{latest['sma_50']:.2f}")
    print(f"     SMA 200: ₹{latest['sma_200']:.2f}")
    print(f"     RSI: {latest['rsi']:.1f}")
    
    if latest['close'] > latest['sma_50'] > latest['sma_200']:
        print(f"     Trend: 🟢 Strong Uptrend")
    elif latest['close'] > latest['sma_50']:
        print(f"     Trend: 🟡 Uptrend")
    elif latest['close'] < latest['sma_50'] < latest['sma_200']:
        print(f"     Trend: 🔴 Downtrend")
    else:
        print(f"     Trend: 🟠 Mixed")
    
    if buy_count > 0:
        print(f"     🎯 {buy_count} BUY signal(s) in last 30 days")
    
    if momentum_count > 0:
        print(f"     🚀 {momentum_count} Momentum signal(s) in last 30 days")

def run_full_scan():
    """
    Run complete stock scan for all tickers
    """
    print("=" * 60)
    print("🔍 STOCK SCANNER - Indian Equities")
    print("=" * 60)
    print(f"Scanning {len(STOCK_UNIVERSE)} stocks...")
    print(f"Lookback period: {LOOKBACK_DAYS} days")
    print(f"Timeout per stock: {FETCH_TIMEOUT} seconds")
    print("")
    
    # Create database
    create_database()
    
    successful_scans = 0
    failed_scans = 0
    
    for ticker in STOCK_UNIVERSE:
        try:
            # Fetch data
            df = fetch_stock_data(ticker, LOOKBACK_DAYS)
            
            if df is None or df.empty:
                failed_scans += 1
                continue
            
            # Calculate indicators
            df = calculate_indicators(df)
            
            # Generate signals
            df = generate_signals(df)
            
            # Save to database
            clean_ticker = ticker.replace('.NS', '')
            save_to_database(df, clean_ticker)
            
            # Print summary
            print_summary(clean_ticker, df)
            
            successful_scans += 1
            
        except Exception as e:
            print(f"  ❌ {ticker}: {str(e)}")
            failed_scans += 1
            continue
    
    print("\n" + "=" * 60)
    print("📊 SCAN SUMMARY")
    print("=" * 60)
    print(f"✅ Successful: {successful_scans}")
    print(f"❌ Failed: {failed_scans}")
    print(f"💾 Database: {DB_PATH}")
    print("")
    print("🎯 Next step: Run 'streamlit run dashboard.py' to view results")
    print("=" * 60)

if __name__ == "__main__":
    run_full_scan()
