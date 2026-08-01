# ⚡ Real-Time Operational Anomaly Engine

![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-1.32.0-FF4B4B?logo=streamlit&logoColor=white)
![DuckDB](https://img.shields.io/badge/DuckDB-0.10.0-FFF000?logo=duckdb&logoColor=black)
![Polars](https://img.shields.io/badge/Polars-Fast-blue)
![Scikit-Learn](https://img.shields.io/badge/Scikit--Learn-ML-F7931E?logo=scikit-learn&logoColor=white)
![GitHub Actions](https://img.shields.io/badge/CI%2FCD-Automated-2088FF?logo=github-actions&logoColor=white)

## 📌 Overview
An end-to-end, zero-maintenance data pipeline and machine learning engine designed to detect structural deviations in high-frequency operational data. Built for speed and efficiency, this architecture ingests live market metrics, calculates rolling statistical features, and flags anomalies using an unsupervised Machine Learning model without human intervention.

## 🏗️ Architecture & Tech Stack

1. **Ingestion & Processing (`Polars`)**: Handles lightning-fast feature engineering (moving averages, z-scores) from live API endpoints.
2. **Storage Layer (`DuckDB`)**: Aggregates and compresses the processed time-series data directly into a highly efficient `Parquet` format.
3. **Machine Learning Brain (`Isolation Forest`)**: Dynamically reads the Parquet data and algorithmically flags the most volatile market events.
4. **CI/CD Automation (`GitHub Actions`)**: A cron job spins up a server every night at midnight UTC to fetch fresh data, run the pipeline, and commit the new data directly to the repository.
5. **Interactive UI (`Streamlit` + `Plotly`)**: A dark-mode dashboard that visualizes the anomalies and allows technical leads to adjust model sensitivity on the fly.

## 🚀 Quick Start (Local Setup)

Clone the repository and spin up the engine locally in seconds.

```bash
# 1. Clone the repo
git clone [https://github.com/DimitriosChrysovalantis/anomaly-engine.git](https://github.com/DimitriosChrysovalantis/anomaly-engine.git)
cd anomaly-engine

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the ingestion pipeline to generate fresh data
python src/pipeline/ingest.py

# 4. Launch the interactive dashboard
streamlit run src/app/main.py

Lets connect:
email: husboula@gmail.com