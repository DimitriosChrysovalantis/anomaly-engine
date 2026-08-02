from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import json
import sqlite3
import numpy as np
import pandas as pd
import yfinance as yf
from sklearn.ensemble import IsolationForest

app = FastAPI(title="Anomaly Engine API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MARKET_CACHE = pd.DataFrame()

# 1. Persistent SQL Ledger (Saves our runs outside of memory)
DB_CONN = sqlite3.connect("quant_ledger.db", check_same_thread=False)
DB_CONN.execute('''
    CREATE TABLE IF NOT EXISTS backtest_runs (
        run_id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        best_sharpe REAL,
        optimal_sl REAL,
        optimal_tp REAL,
        total_trades INTEGER
    )
''')
DB_CONN.commit()

async def fetch_market_data_loop():
    global MARKET_CACHE
    while True:
        try:
            # 2. Multivariate Feature Engineering (Fetching NQ + VIX)
            df_nq = yf.Ticker("NQ=F").history(period="1mo", interval="1h")
            df_vix = yf.Ticker("^VIX").history(period="1mo", interval="1h")
            
            if not df_nq.empty and not df_vix.empty:
                df_nq = df_nq.reset_index()
                df_vix = df_vix.reset_index()
                
                df_nq['timestamp'] = df_nq['Datetime'].dt.strftime('%Y-%m-%d %H:%M:%S')
                df_vix['timestamp'] = df_vix['Datetime'].dt.strftime('%Y-%m-%d %H:%M:%S')
                
                # Merge the two time-series on the timestamp
                df = pd.merge(df_nq, df_vix[['timestamp', 'Close']], on='timestamp', suffixes=('', '_vix'))
                df.rename(columns={'Close': 'value', 'Volume': 'volume', 'Close_vix': 'vix_value'}, inplace=True)
                df = df.drop(columns=['Datetime'], errors='ignore')
                
                # Stationary Features
                df['returns'] = df['value'].pct_change()
                df['volatility'] = df['returns'].rolling(24).std()
                
                mean_24h = df['value'].rolling(24).mean()
                std_24h = df['value'].rolling(24).std()
                df['z_score'] = (df['value'] - mean_24h) / std_24h
                
                vol_mean = df['volume'].rolling(24).mean()
                vol_std = df['volume'].rolling(24).std()
                df['vol_z_score'] = (df['volume'] - vol_mean) / vol_std
                
                # VIX Macro Feature
                vix_mean = df['vix_value'].rolling(24).mean()
                vix_std = df['vix_value'].rolling(24).std()
                df['vix_z_score'] = (df['vix_value'] - vix_mean) / vix_std
                
                MARKET_CACHE = df.dropna().copy()
        except Exception as e:
            print(f"Background worker error: {e}")
        
        await asyncio.sleep(60)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(fetch_market_data_loop())

def process_anomalies(window_days: int):
    global MARKET_CACHE
    if MARKET_CACHE.empty:
        return {"data": [], "metrics": {}}
        
    df = MARKET_CACHE.copy()
    
    if window_days < 30:
        df['dt_temp'] = pd.to_datetime(df['timestamp'])
        min_dt = df['dt_temp'].max() - pd.Timedelta(days=window_days)
        df = df[df['dt_temp'] >= min_dt].drop(columns=['dt_temp'])
    
    if len(df) < 24:
        return {"data": [], "metrics": {}}

    # Base Machine Learning Features (Now explicitly tracking VIX)
    ml_features = ['z_score', 'volume', 'volatility', 'vix_z_score']
    
    # 3. Automated Grid Search Engine
    best_sharpe = -999.0
    best_sl = 1.0
    best_tp = 2.0
    optimal_df = None
    
    # Iterate through 48 combinations of ML Contamination, Stop-Loss, and Take-Profit
    for sensitivity in [0.03, 0.05, 0.08]:
        model = IsolationForest(contamination=sensitivity, random_state=42)
        df_temp = df.copy()
        df_temp['is_anomaly'] = model.fit_predict(df_temp[ml_features]) == -1
        
        next_close = df_temp['value'].shift(-1)
        raw_return = np.where(
            df_temp['is_anomaly'],
            np.where(df_temp['z_score'] < 0, (next_close - df_temp['value']) / df_temp['value'], (df_temp['value'] - next_close) / df_temp['value']),
            0
        )
        
        for sl in [0.5, 1.0, 1.5, 2.5]:
            for tp in [1.0, 2.0, 3.0, 5.0]:
                sl_capped = np.maximum(raw_return, -abs(sl / 100))
                tp_sl_capped = np.minimum(sl_capped, abs(tp / 100))
                
                df_temp['simulated_pnl'] = np.where(df_temp['is_anomaly'], tp_sl_capped * df_temp['value'], 0)
                
                strategy_returns = np.where(df_temp['value'] != 0, df_temp['simulated_pnl'] / df_temp['value'], 0)
                std_ret = strategy_returns.std()
                sharpe = (strategy_returns.mean() / std_ret * np.sqrt(252 * 24)) if std_ret > 0 else 0
                
                if sharpe > best_sharpe:
                    best_sharpe = sharpe
                    best_sl = sl
                    best_tp = tp
                    optimal_df = df_temp.copy()

    # Safety fallback
    if optimal_df is None:
        optimal_df = df

    # Explaining the anomaly (Including the new Macro VIX driver)
    def get_driver(row):
        if not row['is_anomaly']: return None
        if row['vix_z_score'] > 2.5: return "Macro Volatility (VIX)"
        if abs(row['vol_z_score']) > 2.0: return "Liquidity Spike"
        if abs(row['z_score']) > 2.0: return "Price Deviation"
        return "Microstructure Break"
            
    optimal_df['anomaly_driver'] = optimal_df.apply(get_driver, axis=1)
    optimal_df['cumulative_pnl'] = optimal_df['simulated_pnl'].cumsum()
    
    trades = optimal_df[optimal_df['is_anomaly']]
    total_trades = len(trades)
    winning_trades = len(trades[trades['simulated_pnl'] > 0])
    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
    
    rolling_max = optimal_df['cumulative_pnl'].cummax()
    max_dd = (optimal_df['cumulative_pnl'] - rolling_max).min()
    
    # Save optimizer results to the SQL ledger
    if best_sharpe > 0:
        cursor = DB_CONN.cursor()
        cursor.execute('''
            INSERT INTO backtest_runs (best_sharpe, optimal_sl, optimal_tp, total_trades)
            VALUES (?, ?, ?, ?)
        ''', (float(best_sharpe), float(best_sl), float(best_tp), int(total_trades)))
        DB_CONN.commit()

    optimal_df = optimal_df.fillna(0)
    return {
        "data": optimal_df.to_dict(orient="records"),
        "metrics": {
            "sharpe": float(best_sharpe),
            "max_drawdown": float(max_dd),
            "win_rate": float(win_rate),
            "total_trades": int(total_trades),
            "optimal_sl": float(best_sl),
            "optimal_tp": float(best_tp)
        }
    }

@app.websocket("/ws/anomalies")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    window_days = 30
    
    try:
        while True:
            payload = process_anomalies(window_days)
            await websocket.send_json(payload)
            
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=10.0)
                msg = json.loads(data)
                if "window_days" in msg:
                    window_days = int(msg["window_days"])
                    # Send optimized parameters specific to the requested timeframe
                    payload = process_anomalies(window_days)
                    await websocket.send_json(payload)
            except asyncio.TimeoutError:
                continue
    except WebSocketDisconnect:
        print("Client disconnected.")