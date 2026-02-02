import sqlite3
import pandas as pd

conn = sqlite3.connect("scan_results.db")

df = pd.read_sql("""
    SELECT scan_timestamp, COUNT(DISTINCT ticker) AS cnt
    FROM stock_scans
    GROUP BY scan_timestamp
    ORDER BY cnt DESC
""", conn)

conn.close()

print(df.head(10))
print("\nMAX COUNT:", df["cnt"].max())
