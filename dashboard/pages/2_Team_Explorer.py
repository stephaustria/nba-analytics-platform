import plotly.express as px
import streamlit as st

import queries as q

st.set_page_config(page_title="Team Explorer", page_icon="🏀", layout="wide")
st.title("Team Explorer")

teams = q.teams()
names = dict(zip(teams["id"], teams["full_name"]))
left, right = st.columns(2)
tid = left.selectbox("Team", options=list(names), format_func=names.get,
                     index=None, placeholder="Choose a team...")
season = right.selectbox("Season", q.seasons())
if tid is None:
    st.info("Pick a team to get started.")
    st.stop()
tid = int(tid)

games = q.team_games(tid, season)
reg = games[games["season_type"] == "Regular Season"]
if reg.empty:
    st.info("No regular-season games found for this team and season.")
    st.stop()

# ---- headline numbers ----
st.subheader(f"{names[tid]}, {season}")
wins, losses = int((reg["wl"] == "W").sum()), int((reg["wl"] == "L").sum())
cols = st.columns(4)
cols[0].metric("Record", f"{wins}-{losses}")
cols[1].metric("PPG", round(reg["pts"].mean(), 1))
cols[2].metric("Opp PPG", round(reg["opp_pts"].mean(), 1))
cols[3].metric("Avg margin", round(reg["margin"].mean(), 1))

# ---- results chart ----
fig = px.bar(
    reg, x="game_date", y="margin", color="wl",
    color_discrete_map={"W": "#2e7d32", "L": "#c62828"},
    hover_data=["venue", "opp", "pts", "opp_pts"],
    title="Point margin by game",
)
fig.add_scatter(x=reg["game_date"], y=reg["margin"].rolling(10).mean(), mode="lines",
                name="10-game average", line=dict(color="black", width=3))
st.plotly_chart(fig)

# ---- players and schedule ----
st.subheader("Player averages (regular season)")
st.dataframe(q.team_players(tid, season), hide_index=True)

with st.expander("Full schedule and results"):
    st.dataframe(games.sort_values("game_date", ascending=False), hide_index=True)