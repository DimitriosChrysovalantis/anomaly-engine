import polars as pl
import duckdb
import os
import yfinance as yf
import pandas as pd
import ssl

# Global bypass for Mac Python SSL certificate verification error
ssl._create_default_https_context = ssl._create_unverified_context

DATA_DIR = "data"
PARQUET_PATH = os.path.join(DATA_DIR, "metrics.parquet")

def fetch_and_process_data():
    os.makedirs(DATA_DIR, exist_ok=True)
    
    print("1. Fetching raw OHLCV market feed for NQ Futures...")
    
    # Fetch NQ=F (Nasdaq 100 E-mini Futures) hourly data
    df_pd = yf.download("NQ=F", period="1mo", interval="1h", progress=False)
    
    if df_pd.empty:
        print("❌ Error: Could not fetch NQ futures data.")
        return
        
    # Reset index so datetime/date becomes a standard column
    df_pd = df_pd.reset_index()
    
    # Flatten MultiIndex columns if present, otherwise just lowercase them
    if isinstance(df_pd.columns, pd.MultiIndex):
        df_pd.columns = [str(col[0]).lower() for col in df_pd.columns]
    else:
        df_pd.columns = [str(c).lower() for c in df_pd.columns]
        
    # Dynamically find the time column regardless of what yfinance named it
    possible_time_cols = ["datetime", "date", "index", "level_0"]
    time_col = next((col for col in possible_time_cols if col in df_pd.columns), None)
    
    if not time_col:
        # Fallback: just take the very first column since time is always index 0 after reset_index()
        time_col = df_pd.columns[0]
        
    df_pd = df_pd.rename(columns={time_col: "timestamp"})
    
    # Ensure timestamp is datetime type and strip timezone
    df_pd['timestamp'] = pd.to_datetime(df_pd['timestamp'])
    if df_pd['timestamp'].dt.tz is not None:
        df_pd['timestamp'] = df_pd['timestamp'].dt.tz_localize(None)

    # Convert to Polars for lightning-fast feature processing
    df_raw = pl.from_pandas(df_pd)
    
    print("2. Processing multivariate features...")
    df_processed = (
        df_raw
        .select([
            pl.col("timestamp"),
            pl.col("open").cast(pl.Float64),
            pl.col("high").cast(pl.Float64),
            pl.col("low").cast(pl.Float64),
            pl.col("close").cast(pl.Float64).alias("value"),
            pl.col("volume").cast(pl.Float64)
        ])
        .with_columns([
            pl.col("value").pct_change().alias("returns"),
            pl.col("value").rolling_mean(window_size=24).alias("rolling_mean_24h"),
            pl.col("value").rolling_std(window_size=24).alias("rolling_std_24h"),
            (pl.col("high") - pl.col("low")).alias("candle_spread")
        ])
        .filter(pl.col("rolling_mean_24h").is_not_null())
    )

    print("3. Aggregating and compressing to Parquet...")
    con = duckdb.connect()
    con.register("df_polars", df_processed.to_pandas())
    
    con.execute(f"""
        COPY (
            SELECT 
                timestamp, open, high, low, value, volume, returns,
                rolling_mean_24h, rolling_std_24h, candle_spread,
                (value - rolling_mean_24h) / NULLIF(rolling_std_24h, 0) AS z_score
            FROM df_polars
            ORDER BY timestamp DESC
        ) TO '{PARQUET_PATH}' (FORMAT PARQUET);
    """)
    con.close()
    
    print(f"✅ NQ Futures Pipeline complete.")

if __name__ == "__main__":
    fetch_and_process_data()