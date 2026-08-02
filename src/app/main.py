import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import sys
import os
import pandas as pd

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from src.models.detector import run_anomaly_detection

st.set_page_config(page_title="Quantitative Anomaly Terminal", page_icon="📈", layout="wide")

# --- PERFORMANCE OPTIMIZATION (Hiring managers look for this) ---
@st.cache_data(ttl=3600, show_spinner=False)
def load_and_score_data(sensitivity):
    """Caches the ML scoring process so the UI doesn't freeze on reload."""
    df_pl = run_anomaly_detection(contamination=sensitivity)
    return df_pl.to_pandas()

# --- UI HEADER ---
st.title("📈 Quantitative Anomaly Terminal")
st.markdown("""
<span style="color:#888888">Institutional-grade structural deviation detection. Market data processed via DuckDB and scored via Unsupervised ML.</span>
""", unsafe_allow_html=True)
st.divider()

# --- SIDEBAR CONTROLS ---
with st.sidebar:
    st.header("Risk Parameters")
    sensitivity = st.slider("Model Contamination Rate", 0.01, 0.15, 0.05, 0.01)
    st.caption("Adjusts the Isolation Forest boundary. Higher values flag more events.")
    
    # Load data with cached function
    with st.spinner("Scoring Data Matrix..."):
        df = load_and_score_data(sensitivity)
    
    st.divider()
    st.subheader("Export Data")
    # Provide a clean CSV export of just the anomalies
    anomalies_only = df[df['is_anomaly']]
    csv = anomalies_only.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Download Incident Report",
        data=csv,
        file_name='anomaly_incident_report.csv',
        mime='text/csv',
    )

# --- TOP LEVEL METRICS ---
col1, col2, col3, col4 = st.columns(4)
latest = df.iloc[-1]
previous = df.iloc[-2]

col1.metric("Live Execution Price", f"${latest['value']:,.2f}", f"{latest['returns']*100:.2f}%")
col2.metric("Identified Deviations", int(df["is_anomaly"].sum()))
col3.metric("Current Z-Score", f"{latest['z_score']:.2f}")
col4.metric("24h Volatility Spread", f"${latest['candle_spread']:,.2f}")

# --- ADVANCED CHARTING (TradingView Style) ---
# Create a chart with 2 rows (Price/Anomalies on top, Volume on bottom)
fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                    vertical_spacing=0.03, row_heights=[0.7, 0.3])

# 1. Candlestick Trace
fig.add_trace(go.Candlestick(
    x=df['timestamp'], open=df['open'], high=df['high'],
    low=df['low'], close=df['value'], name='Market Action'
), row=1, col=1)

# 2. Bollinger Bands (Upper and Lower)
df['upper_band'] = df['rolling_mean_24h'] + (df['rolling_std_24h'] * 2)
df['lower_band'] = df['rolling_mean_24h'] - (df['rolling_std_24h'] * 2)

fig.add_trace(go.Scatter(
    x=df['timestamp'], y=df['upper_band'], mode='lines', 
    line=dict(color='rgba(255,255,255,0.2)', width=1), name='Upper Band'
), row=1, col=1)

fig.add_trace(go.Scatter(
    x=df['timestamp'], y=df['lower_band'], mode='lines', 
    line=dict(color='rgba(255,255,255,0.2)', width=1), fill='tonexty', 
    fillcolor='rgba(255,255,255,0.05)', name='Lower Band'
), row=1, col=1)

# 3. Anomaly Markers (The "Kill Switch" flags)
anomalies = df[df['is_anomaly']]
fig.add_trace(go.Scatter(
    x=anomalies['timestamp'], y=anomalies['value'],
    mode='markers', name='Structural Deviation',
    marker=dict(color='#FF2A6D', size=10, symbol='diamond-open', line=dict(width=2))
), row=1, col=1)

# 4. Volume Bar Chart
colors = ['#00D2FF' if row['open'] - row['value'] >= 0 else '#FF2A6D' for index, row in df.iterrows()]
fig.add_trace(go.Bar(
    x=df['timestamp'], y=df['volume'], marker_color=colors, name='Volume'
), row=2, col=1)

# Update layout to look sleek and professional
fig.update_layout(
    template="plotly_dark",
    height=700, margin=dict(l=0, r=0, t=10, b=0),
    xaxis_rangeslider_visible=False,
    showlegend=False
)

st.plotly_chart(fig, use_container_width=True)

# --- INCIDENT LOG TABLE ---
st.subheader("Deviation Log")
st.dataframe(
    anomalies[["timestamp", "value", "returns", "z_score", "candle_spread"]].sort_values("timestamp", ascending=False),
    use_container_width=True,
    hide_index=True
)