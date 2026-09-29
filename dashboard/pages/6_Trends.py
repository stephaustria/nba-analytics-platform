import plotly.graph_objects as go
import streamlit as st

import queries as q
from analytics import metrics

st.set_page_config(page_title="Trends", page_icon="🏀", layout="wide")
st.title("Player Trends")

players = q.players_with_stats()
names = dict(zip(players["id"], players["full_name"]))
c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
pid = c1.selectbox("Player", options=list(names), format_func=names.get,
                   index=None, placeholder="Start typing a name...")
season = c2.selectbox("Season", q.seasons())
stat = c3.selectbox("Stat", ["pts", "reb", "ast", "game_score", "plus_minus"])
window = c4.slider("Window (games)", 3, 20, 5)
if pid is None:
    st.info("Pick a player to get started.")
    st.stop()

log = q.player_log(int(pid), season)
log = log[log["season_type"] == "Regular Season"].reset_index(drop=True)
if len(log) < window:
    st.info("Not enough games for that window.")
    st.stop()
log["game_score"] = metrics.game_score(log)

values = log[stat]
rolling = values.rolling(window).mean()
season_avg, spread = values.mean(), values.std()

m1, m2, m3 = st.columns(3)
m1.metric("Season average", round(season_avg, 1))
m2.metric(f"Last {window} games", round(values.tail(window).mean(), 1),
          delta=round(values.tail(window).mean() - season_avg, 1))
m3.metric("Games", len(log))

fig = go.Figure()
fig.add_hrect(y0=season_avg - spread, y1=season_avg + spread, fillcolor="gray",
              opacity=0.12, line_width=0)
fig.add_hline(y=season_avg, line_dash="dot", annotation_text="season average")
fig.add_scatter(x=log["game_date"], y=values, mode="markers", name="Game",
                marker=dict(size=7, opacity=0.5), customdata=log[["opp", "venue"]],
                hovertemplate="%{x|%b %d}: %{y} (%{customdata[1]} %{customdata[0]})<extra></extra>")
fig.add_scatter(x=log["game_date"], y=rolling, mode="lines", name=f"{window}-game average",
                line=dict(width=3))
fig.update_layout(title=f"{names[int(pid)]}: {stat} in {season} (gray band = ±1 std dev)")
st.plotly_chart(fig)

# ---- best and worst stretches ----
best, worst = rolling.idxmax(), rolling.idxmin()
for label, idx in (("Hottest", best), ("Coldest", worst)):
    start, end = log["game_date"][idx - window + 1], log["game_date"][idx]
    st.write(f"**{label} {window}-game stretch:** {start:%b %d} to {end:%b %d}, "
             f"averaging {rolling[idx]:.1f}")