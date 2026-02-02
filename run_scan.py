import sqlite3
import pandas as pd
import logging
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from math import ceil

from main import analyze_stock

# =============================
# CONFIG
# =============================
DB_FILE = "scan_results.db"
TABLE = "stock_scans"

BATCH_SIZE = 10
MAX_WORKERS = 6

LOG_FILE = "scan.log"

# =============================
# LOGGING
# =============================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)

log = logging.getLogger(__name__)

# =============================
# NSE UNIVERSE
# =============================
FALLBACK_NIFTY50 = [
    "ADANIENT.NS","ADANIPORTS.NS","APOLLOHOSP.NS","ASIANPAINT.NS",
    "AXISBANK.NS","BAJAJ-AUTO.NS","BAJFINANCE.NS","BAJAJFINSV.NS",
    "BPCL.NS","BHARTIARTL.NS","BRITANNIA.NS","CIPLA.NS","COALINDIA.NS",
    "DIVISLAB.NS","DRREDDY.NS","EICHERMOT.NS","GRASIM.NS","HCLTECH.NS",
    "HDFCBANK.NS","HDFCLIFE.NS","HEROMOTOCO.NS","HINDALCO.NS",
    "HINDUNILVR.NS","ICICIBANK.NS","ITC.NS","INDUSINDBK.NS",
    "INFY.NS","JSWSTEEL.NS","KOTAKBANK.NS","LT.NS","M&M.NS",
    "MARUTI.NS","NTPC.NS","NESTLEIND.NS","ONGC.NS","POWERGRID.NS",
    "RELIANCE.NS","SBIN.NS","SUNPHARMA.NS","TATAMOTORS.NS",
    "TATASTEEL.NS","TCS.NS","TECHM.NS","TITAN.NS","ULTRACEMCO.NS",
    "UPL.NS","WIPRO.NS"
]

def fetch_nifty50():
    """
    Tries NSE website.
    Falls back safely if NSE blocks or times out.
    """
    url = "https://www.niftyindices.com/IndexConstituent/ind_nifty50list.csv"
    try:
        log.info("Fetching NIFTY 50 from NSE")
        df = pd.read_csv(url)
        symbols = [s.strip() + ".NS" for s in df["Symbol"].tolist()]
        log.info(f"NSE fetch successful: {len(symbols)} stocks")
        return symbols
    except Exception as e:
        log.warning(f"NSE fetch failed, using fallback list | {e}")
        return FALLBACK_NIFTY50

# =============================
# DB
# =============================
def init_db():
    conn = sqlite3.connect(DB_FILE)
    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS {TABLE} (
            ticker TEXT,
            price REAL,
            RSI REAL,
            buy_sharpe REAL,
            buy_return_pct REAL,
            buy_max_dd REAL,
            mom_sharpe REAL,
            mom_return_pct REAL,
            mom_max_dd REAL,
            scan_timestamp TEXT
        )
    """)
    conn.commit()
    conn.close()

def save(df):
    conn = sqlite3.connect(DB_FILE)
    df.to_sql(TABLE, conn, if_exists="append", index=False)
    conn.close()

# =============================
# SCAN
# =============================
def scan_batch(symbols):
    results = []
    with ThreadPoolExecutor(MAX_WORKERS) as ex:
        futures = {ex.submit(analyze_stock, s): s for s in symbols}
        for f in as_completed(futures):
            sym = futures[f]
            try:
                results.append(f.result())
            except Exception as e:
                log.error(f"Failed: {sym} | {e}")
    return results

# =============================
# MAIN
# =============================
if __name__ == "__main__":
    init_db()

    symbols = fetch_nifty50()
    total = len(symbols)

    if total == 0:
        raise RuntimeError("No symbols to scan")

    SCAN_TS = datetime.now().isoformat()
    all_results = []

    batches = ceil(total / BATCH_SIZE)
    log.info(f"Starting scan | {total} stocks | {batches} batches")

    for i in range(batches):
        batch = symbols[i * BATCH_SIZE:(i + 1) * BATCH_SIZE]
        log.info(f"Scanning batch {i+1}/{batches}")
        batch_results = scan_batch(batch)
        all_results.extend(batch_results)

    if not all_results:
        raise RuntimeError("Scan failed completely")

    df = pd.DataFrame(all_results)
    df["scan_timestamp"] = SCAN_TS
    save(df)

    log.info(f"✅ Scan complete — {len(df)} stocks saved")
