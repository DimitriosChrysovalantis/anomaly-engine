import streamlit as st
import plotly.graph_objects as go
import sys
import os

# Ensure Python can find our local modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from src.models.detector import run_anomaly_detection

# Configure the visual layout
st.set_page_config(
    page_title="Real-Time Signal Engine",
    page_icon="⚡",
    layout="wide"
)

st.title("⚡ Real-Time Operational Anomaly Engine")
st.caption("Powered by DuckDB, Polars, Isolation Forest, and Streamlit")

# Sidebar Controls for the ML Model
st.sidebar.header("Model Parameters")
sensitivity = st.sidebar.slider(
    "Anomaly Sensitivity", 
    min_value=0.01, 
    max_value=0.15, 
    value=0.05, 
    step=0.01,
    help="Higher values flag more data points as anomalous."
)

# Fetch Data & Run Model dynamically based on the slider
with st.spinner("Executing DuckDB queries & scoring model..."):
    # Run the model and convert to pandas for Streamlit/Plotly compatibility
    df_pl = run_anomaly_detection(contamination=sensitivity)
    df = df_pl.to_pandas()

# Top Metrics Row
col1, col2, col3 = st.columns(3)
col1.metric("Total Data Points", f"{len(df):,}")
col2.metric("Anomalies Detected", int(df["is_anomaly"].sum()))
col3.metric("Latest Signal Value", f"${df['value'].iloc[-1]:,.2f}")

# Plotly Interactive Chart
fig = go.Figure()

# Normal Baseline Line
fig.add_trace(go.Scatter(
    x=df['timestamp'], y=df['value'],
    mode='lines', name='Signal Value',
    line=dict(color='#00D2FF', width=1.5)
))

# Anomalies Marker Overlay
anomalies = df[df['is_anomaly']]
fig.add_trace(go.Scatter(
    x=anomalies['timestamp'], y=anomalies['value'],
    mode='markers', name='Anomaly Flagged',
    marker=dict(color='#FF2A6D', size=8, symbol='x')
))

fig.update_layout(
    template="plotly_dark",
    margin=dict(l=20, r=20, t=30, b=20),
    height=500,
    xaxis_title="Time",
    yaxis_title="Value (USD)"
)

st.plotly_chart(fig, use_container_width=True)

# Data Table for Deep Dive
st.subheader("Anomalous Event Log")
st.dataframe(
    anomalies[["timestamp", "value", "returns", "z_score"]].sort_values("timestamp", ascending=False),
    use_container_width=True
)