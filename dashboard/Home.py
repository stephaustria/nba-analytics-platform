import plotly.express as px
import streamlit as st

import queries as q

st.set_page_config(page_title="NBA Analytics Platform", page_icon="🏀", layout="wide")
st.title("🏀 NBA Analytics Platform")

all_seasons = q.seasons()
if not all_seasons:
    st.warning("No data found. Run `python -m pipeline.ingest` first.")
    st.stop()

season = st.sidebar.selectbox("Season", all_seasons)
min_games = st.sidebar.slider("Minimum games for leaders", 1, 82, 30)

# ---- standings ----
st.subheader(f"{season} regular season standings")
standings = q.standings(season)
table = standings[["full_name", "gp", "wins", "losses", "win_pct", "ppg", "margin"]].copy()
table.columns = ["Team", "GP", "W", "L", "Win %", "PPG", "Avg margin"]
table.index = range(1, len(table) + 1)
st.dataframe(table, height=600)

# ---- scoring vs. point differential ----
fig = px.scatter(
    standings, x="ppg", y="margin", text="abbreviation", hover_name="full_name",
    labels={"ppg": "Points per game", "margin": "Average point differential"},
    title="Scoring vs. point differential",
)
fig.update_traces(textposition="top center")
st.plotly_chart(fig)

# ---- league leaders ----
st.subheader("League leaders (per game)")
tabs = st.tabs(list(q.STAT_COLS))
for tab, label in zip(tabs, q.STAT_COLS):
    with tab:
        df = q.leaders(season, label, min_games)
        left, right = st.columns([1, 2])
        left.dataframe(df, hide_index=True)
        right.plotly_chart(
            px.bar(df.sort_values("per_game"), x="per_game", y="player", orientation="h",
                   labels={"per_game": label, "player": ""})
        )
        