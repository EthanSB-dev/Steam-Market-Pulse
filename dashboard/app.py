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

# --- Engagement by genre ---
st.header("Engagement by Genre (Concurrent Players)")
st.caption(
    "SteamSpy's playtime data was found unusable for every tracked game (a 2018 "
    "Steam privacy change broke third-party playtime sampling site-wide) - "
    "concurrent players are used here as a more reliable engagement proxy. "
    "Genres with fewer than 3 tracked games are excluded to avoid single-game skew."
)

genre_df = pd.read_sql("""
    SELECT g.genre_name,
           COUNT(DISTINCT a.appid) AS games_in_genre,
           ROUND(AVG(p.concurrent_players)) AS avg_concurrent_players
    FROM player_snapshots p
    JOIN apps a ON a.appid = p.appid
    JOIN app_genres ag ON ag.appid = a.appid
    JOIN genres g ON g.genre_id = ag.genre_id
    GROUP BY g.genre_name
    HAVING COUNT(DISTINCT a.appid) >= 3
    ORDER BY avg_concurrent_players DESC
""", engine)

fig_genre = px.bar(
    genre_df, x="avg_concurrent_players", y="genre_name", orientation="h",
    labels={"avg_concurrent_players": "Avg Concurrent Players", "genre_name": ""},
    hover_data=["games_in_genre"],
)
fig_genre.update_layout(yaxis={"categoryorder": "total ascending"})
st.plotly_chart(fig_genre, use_container_width=True)

# --- Per-game time series ---
st.header("Player Count Over Time")

game_list = pd.read_sql("SELECT appid, name FROM apps ORDER BY name", engine)
selected_name = st.selectbox("Choose a game", game_list["name"])
selected_appid = int(game_list.loc[game_list["name"] == selected_name, "appid"].iloc[0])

timeseries_query = text("""
    SELECT captured_at, concurrent_players
    FROM player_snapshots
    WHERE appid = :appid
    ORDER BY captured_at
""")
timeseries_df = pd.read_sql(timeseries_query, engine, params={"appid": selected_appid})

if timeseries_df.empty:
    st.info("No snapshots collected yet for this game.")
else:
    fig_ts = px.line(
        timeseries_df, x="captured_at", y="concurrent_players",
        labels={"captured_at": "Time", "concurrent_players": "Concurrent Players"},
    )
    st.plotly_chart(fig_ts, use_container_width=True)