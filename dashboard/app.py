"""
Streamlit dashboard. Lets the user pick which data source to view from
a sidebar dropdown, then renders a source-appropriate chart.

Run with:
    streamlit run dashboard/app.py
"""

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

# Allow running `streamlit run dashboard/app.py` from the repo root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import config, db  # noqa: E402

st.set_page_config(
    page_title="Daily Dashboard",
    layout="wide",
    menu_items={
        "Get help": None,
        "Report a bug": None,
        "About": None,
    },
)

SOURCE_LABELS = {
    "weather": "Weather",
    "stocks": "Stocks / crypto",
    "sports": "Sports",
    "air_quality": "Air quality",
    "habits": "GitHub habits",
}

st.title("Daily Dashboard")
st.caption("Data refreshed daily by a scheduled GitHub Actions job.")

db.init_db(config.DB_PATH)
available_sources = db.distinct_sources(config.DB_PATH)

if not available_sources:
    st.info(
        "No data yet. Run `python -m src.ingest` once locally to populate "
        "the database, then refresh this page."
    )
    st.stop()

source = st.sidebar.selectbox(
    "Data source",
    options=available_sources,
    format_func=lambda s: SOURCE_LABELS.get(s, s),
)

rows = db.query_source(config.DB_PATH, source, limit=1000)
df = pd.DataFrame(rows)

if df.empty:
    st.warning(f"No rows found for source '{source}' yet.")
    st.stop()

df["timestamp"] = pd.to_datetime(df["timestamp"])

st.subheader(SOURCE_LABELS.get(source, source))

metrics = sorted(df["metric"].unique())
metric = st.sidebar.selectbox("Metric", options=metrics)

metric_df = df[df["metric"] == metric].sort_values("timestamp")

col1, col2 = st.columns([3, 1])

with col1:
    if metric_df["label"].nunique() > 1:
        pivot = metric_df.pivot_table(
            index="timestamp", columns="label", values="value", aggfunc="last"
        )
        st.line_chart(pivot)
    else:
        st.line_chart(metric_df.set_index("timestamp")["value"])

with col2:
    latest = metric_df.sort_values("timestamp").iloc[-1]
    st.metric(label=f"Latest {metric}", value=f"{latest['value']:.2f}")
    st.caption(f"Label: {latest['label']}")
    st.caption(f"As of: {latest['timestamp']}")

with st.expander("Raw data"):
    st.dataframe(metric_df.sort_values("timestamp", ascending=False), use_container_width=True)
