import duckdb
import polars as pl
from sklearn.ensemble import IsolationForest
import numpy as np
import os

def run_anomaly_detection(parquet_path="data/metrics.parquet", contamination=0.05):
    # Make sure the file exists before trying to read it
    if not os.path.exists(parquet_path):
        raise FileNotFoundError(f"Could not find {parquet_path}. Run ingest.py first.")

    # 1. Query parquet directly using DuckDB and convert back to Polars
    con = duckdb.connect()
    df = con.execute(f"SELECT * FROM '{parquet_path}' ORDER BY timestamp ASC").pl()
    con.close()

    # 2. Prepare features for ML model (we use returns and z-score for stable signals)
    features = df.select(["returns", "z_score"]).to_numpy()
    
    # Clean up any weird NaNs just in case
    features = np.nan_to_num(features)

    # 3. Train the Unsupervised ML Model (Isolation Forest)
    # Contamination defines what % of data we expect to be an anomaly
    model = IsolationForest(contamination=contamination, random_state=42)
    
    # Predict (-1 means anomaly, 1 means normal)
    predictions = model.fit_predict(features)
    
    # 4. Bind the predictions back to our Polars dataframe
    df = df.with_columns(
        pl.Series(name="anomaly_label", values=predictions)
    )

    # Create a clean boolean column for the frontend to use
    df = df.with_columns(
        pl.when(pl.col("anomaly_label") == -1)
        .then(pl.lit(True))
        .otherwise(pl.lit(False))
        .alias("is_anomaly")
    )
    
    return df

if __name__ == "__main__":
    print("Initializing ML Anomaly Engine...")
    df_scored = run_anomaly_detection()
    
    anomalies = df_scored.filter(pl.col("is_anomaly") == True)
    print(f"✅ ML Engine Run Complete.")
    print(f"Detected {len(anomalies)} anomalous events out of {len(df_scored)} total hours.")