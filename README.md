# 📈 NQ Futures Anomaly Engine

An end-to-end quantitative trading microservice that streams real-time Nasdaq (NQ) and VIX market data, detects microstructural anomalies using an Isolation Forest machine learning model, and dynamically optimizes trading parameters via a vectorized grid search.

![Architecture](https://img.shields.io/badge/Architecture-Microservices-blue)
![Backend](https://img.shields.io/badge/Backend-FastAPI%20%7C%20Python-3776AB?logo=python&logoColor=white)
![Frontend](https://img.shields.io/badge/Frontend-React%20%7C%20Vite-61DAFB?logo=react&logoColor=black)
![Infrastructure](https://img.shields.io/badge/Deployment-Docker%20Compose-2496ED?logo=docker&logoColor=white)

## 🏗 System Architecture

The application is fully containerized and decoupled into three operational layers:

1. **The In-Memory Data Pipeline (Python/Pandas):** 
   A continuous background worker pulls live OHLCV data for NQ Futures and the CBOE Volatility Index (VIX), calculates rolling Z-scores, and merges them into a synchronized time-series cache.
2. **The ML & Optimizer Engine (Scikit-Learn/Numpy):**
   Executes an unsupervised Isolation Forest model to detect market structure breaks. An algorithmic grid search vectorizes 48 combinations of Stop-Loss, Take-Profit, and ML Sensitivity parameters to find the highest Sharpe Ratio for the current market regime. Results are committed to a persistent SQLite database.
3. **The Trading Terminal (React/WebSockets/TradingView):**
   A React frontend establishes a persistent WSS tunnel to the FastAPI backend, rendering sub-second ML inferences and backtest metrics onto a high-performance TradingView Lightweight Chart canvas.

## 🚀 Quick Start

The entire stack is containerized. To spin up the backend ML engine and the frontend trading terminal locally:

1. Ensure Docker Desktop is running.
2. Clone the repository and navigate to the root folder.
3. Boot the microservices:
   ```bash
   docker-compose up --build

Navigate to http://localhost:5173 in your browser.

