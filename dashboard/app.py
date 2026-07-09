import os
import sys

import pandas as pd
import plotly.express as px
import streamlit as st
from sqlalchemy import text

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src", "db"))
from connection import get_engine

st.set_page_config(page_title="Steam Market Pulse", layout="wide")

st.title("🎮 Steam Market Pulse")
st.caption(
    "A market-health dashboard built on live Steam data — ownership, "
    "engagement, and pricing trends across 50 tracked titles."
)

engine = get_engine()

# --- Overview metrics ---
overview = pd.read_sql("""
    SELECT
        (SELECT COUNT(*) FROM apps) AS total_games,
        (SELECT COUNT(*) FROM player_snapshots) AS total_snapshots,
        (SELECT MAX(captured_at) FROM player_snapshots) AS last_updated
""", engine).iloc[0]

col1, col2, col3 = st.columns(3)
col1.metric("Games Tracked", int(overview["total_games"]))
col2.metric("Snapshots Collected", int(overview["total_snapshots"]))
col3.metric("Last Updated", str(overview["last_updated"]))

# --- Most owned games ---
st.header("Most Owned Games")

owned_df = pd.read_sql("""
    SELECT a.name,
           ROUND((o.owners_low + o.owners_high) / 2.0) AS owners_estimate
    FROM ownership_stats o
    JOIN apps a ON a.appid = o.appid
    ORDER BY owners_estimate DESC
    LIMIT 15
""", engine)

fig = px.bar(
    owned_df, x="owners_estimate", y="name", orientation="h",
    labels={"owners_estimate": "Estimated Owners", "name": ""},
)
fig.update_layout(yaxis={"categoryorder": "total ascending"})
st.plotly_chart(fig, use_container_width=True)