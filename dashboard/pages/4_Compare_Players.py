import pandas as pd
import plotly.express as px
import streamlit as st

import queries as q

st.set_page_config(page_title="Compare Players", page_icon="🏀", layout="wide")
st.title("Compare Players")

players = q.players_with_stats()
names = dict(zip(players["id"], players["full_name"]))

season = st.selectbox("Season (regular season)", q.seasons())
c1, c2 = st.columns(2)
a = c1.selectbox("Player A", options=list(names), format_func=names.get, index=None, placeholder="Choose...")
b = c2.selectbox("Player B", options=list(names), format_func=names.get, index=None, placeholder="Choose...")
if a is None or b is None:
    st.info("Pick two players.")
    st.stop()
if a == b:
    st.warning("Pick two different players.")
    st.stop()


def season_row(pid: int):
    df = q.player_seasons(int(pid))
    r = df[(df["season"] == season) & (df["season_type"] == "Regular Season")]
    return None if r.empty else r.iloc[0]


ra, rb = season_row(a), season_row(b)
missing = [names[p] for p, r in ((a, ra), (b, rb)) if r is None]
if missing:
    st.warning(f"No regular-season games in {season} for: {', '.join(missing)}")
    st.stop()

# ---- counting stats chart ----
stats = ["ppg", "rpg", "apg", "spg", "bpg", "topg"]
chart_df = pd.DataFrame({
    "Stat": stats * 2,
    "Player": [names[a]] * len(stats) + [names[b]] * len(stats),
    "Value": [ra[s] for s in stats] + [rb[s] for s in stats],
})
st.plotly_chart(px.bar(chart_df, x="Stat", y="Value", color="Player", barmode="group",
                       title=f"Per-game comparison, {season}"))

# ---- full table ----
cols = ["gp", "mpg", "ppg", "rpg", "apg", "spg", "bpg", "topg", "fg_pct", "fg3_pct", "ft_pct"]
st.dataframe(pd.DataFrame({names[a]: ra[cols], names[b]: rb[cols]}))
