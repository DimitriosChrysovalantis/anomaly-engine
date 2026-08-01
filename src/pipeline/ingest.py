import polars as pl
import duckdb
import os
import urllib.request
import json
import ssl

# Save directly inside the project root's data/ folder
DATA_DIR = "data"
PARQUET_PATH = os.path.join(DATA_DIR, "metrics.parquet")

def fetch_and_process_data():
    # Ensure the data folder exists inside anomaly-engine
    os.makedirs(DATA_DIR, exist_ok=True)
    
    # Using Binance API
    url = "https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=1h&limit=1000"
    print("1. Fetching raw operational feed...")
    
    # Bypass Mac Python SSL certificate verification error
    ssl_context = ssl._create_unverified_context()
    
    # Fetch data from URL using urllib
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, context=ssl_context) as response:
        raw_data = json.loads(response.read().decode())
        
    # Binance returns lists. Index 0 is timestamp(ms), Index 4 is Close Price.
    df_raw = pl.DataFrame({
        "timestamp_ms": [row[0] for row in raw_data],
        "value": [float(row[4]) for row in raw_data]
    })
    
    print("2. Processing features with Polars...")
    # Clean the data and calculate rolling statistics (moving averages, std dev)
    df_processed = (
        df_raw
        .with_columns([
            pl.col("timestamp_ms").cast(pl.Datetime("ms")).alias("timestamp"),
            pl.col("value").pct_change().alias("returns"),
            pl.col("value").rolling_mean(window_size=24).alias("rolling_mean_24h"),
            pl.col("value").rolling_std(window_size=24).alias("rolling_std_24h"),
        ])
        .filter(pl.col("rolling_mean_24h").is_not_null())
    )

    print("3. Aggregating and compressing with DuckDB...")
    # Use DuckDB to calculate z-scores and save directly to Parquet format
    con = duckdb.connect()
    con.register("df_polars", df_processed.to_pandas())
    
    con.execute(f"""
        COPY (
            SELECT 
                timestamp,
                value,
                returns,
                rolling_mean_24h,
                rolling_std_24h,
                (value - rolling_mean_24h) / NULLIF(rolling_std_24h, 0) AS z_score
            FROM df_polars
            ORDER BY timestamp DESC
        ) TO '{PARQUET_PATH}' (FORMAT PARQUET);
    """)
    con.close()
    
    print(f"✅ Pipeline complete. Parquet stored at: {PARQUET_PATH}")

if __name__ == "__main__":
    fetch_and_process_data()