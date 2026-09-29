import plotly.express as px
import streamlit as st

import queries as q

st.set_page_config(page_title="Player Explorer", page_icon="🏀", layout="wide")
st.title("Player Explorer")

players = q.players_with_stats()
names = dict(zip(players["id"], players["full_name"]))
pid = st.selectbox("Player (type to search)", options=list(names), format_func=names.get,
                   index=None, placeholder="Start typing a name...")
if pid is None:
    st.info("Pick a player to get started.")
    st.stop()
pid = int(pid)

seasons_df = q.player_seasons(pid)
reg = seasons_df[seasons_df["season_type"] == "Regular Season"]
season = st.selectbox("Season", sorted(seasons_df["season"].unique(), reverse=True))

# ---- headline numbers ----
st.subheader(f"{names[pid]}, {season}")
row = reg[reg["season"] == season]
if row.empty:
    st.caption("No regular-season games this season.")
else:
    r = row.iloc[0]
    cols = st.columns(7)
    cols[0].metric("GP", int(r["gp"]))
    cols[1].metric("PPG", r["ppg"])
    cols[2].metric("RPG", r["rpg"])
    cols[3].metric("APG", r["apg"])
    cols[4].metric("FG%", f"{r['fg_pct']:.1%}" if r["fg_pct"] == r["fg_pct"] else "-")
    cols[5].metric("3P%", f"{r['fg3_pct']:.1%}" if r["fg3_pct"] == r["fg3_pct"] else "-")
    cols[6].metric("FT%", f"{r['ft_pct']:.1%}" if r["ft_pct"] == r["ft_pct"] else "-")

# ---- trend across seasons ----
st.plotly_chart(
    px.line(reg, x="season", y=["ppg", "rpg", "apg"], markers=True,
            title="Regular-season averages by season",
            labels={"value": "Per game", "variable": "Stat"})
)

with st.expander("All seasons (regular season and playoffs)"):
    st.dataframe(seasons_df, hide_index=True)

# ---- game log ----
st.subheader("Game log")
log = q.player_log(pid, season)
if log.empty:
    st.info("No games found.")
    st.stop()

stat = st.radio("Stat", ["pts", "reb", "ast"], horizontal=True)
fig = px.bar(
    log, x="game_date", y=stat, color="result",
    color_discrete_map={"W": "#2e7d32", "L": "#c62828"},
    hover_data=["venue", "opp", "minutes"],
    title=f"{stat.upper()} per game (green = team win)",
)
fig.add_scatter(x=log["game_date"], y=log[stat].rolling(5).mean(), mode="lines",
                name="5-game average", line=dict(color="black", width=3))
st.plotly_chart(fig)
st.dataframe(log.drop(columns=["margin"]).sort_values("game_date", ascending=False), hide_index=True)