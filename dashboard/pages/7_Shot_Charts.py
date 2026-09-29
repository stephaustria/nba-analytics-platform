import plotly.graph_objects as go
import streamlit as st

import queries as q
from court import court_traces

st.set_page_config(page_title="Shot Charts", page_icon="🏀", layout="wide")
st.title("Shot Charts")

season = st.sidebar.selectbox("Season", q.seasons())
players = q.shot_players(season)
if players.empty:
    st.info("No shot data for this season. Run `python -m pipeline.shots --season "
            f"{season} --top 100`.")
    st.stop()

names = dict(zip(players["id"], players["full_name"]))
pid = st.selectbox("Player", options=list(names), format_func=names.get,
                   index=None, placeholder="Start typing a name...")
if pid is None:
    st.stop()

df = q.shots(int(pid), season)
kind = st.radio("Shot type", ["All", "2PT", "3PT"], horizontal=True)
if kind != "All":
    df = df[df["shot_type"].str.startswith(kind[0])]
if df.empty:
    st.info("No shots found.")
    st.stop()

# ---- headline numbers ----
df = df.assign(points=df["made"] * df["shot_type"].str.startswith("3").map({True: 3, False: 2}))
c1, c2, c3 = st.columns(3)
c1.metric("Attempts", len(df))
c2.metric("FG%", f"{df['made'].mean():.1%}")
c3.metric("Points per shot", round(df["points"].sum() / len(df), 2))

# ---- court ----
fig = go.Figure(court_traces())
for made, symbol, color, name in ((True, "circle-open", "#2e7d32", "Made"),
                                  (False, "x", "#c62828", "Missed")):
    sub = df[df["made"] == made]
    fig.add_scatter(
        x=sub["loc_x"], y=sub["loc_y"], mode="markers", name=name, opacity=0.7,
        marker=dict(symbol=symbol, color=color, size=8),
        customdata=sub[["action_type", "distance"]],
        hovertemplate="%{customdata[0]}<br>%{customdata[1]} ft<extra></extra>",
    )
fig.update_xaxes(range=[-260, 260], visible=False)
fig.update_yaxes(range=[-55, 425], visible=False, scaleanchor="x", scaleratio=1)
fig.update_layout(height=700, plot_bgcolor="white", title=f"{names[int(pid)]}, {season}")
st.plotly_chart(fig)

# ---- zone efficiency ----
st.subheader("Efficiency by zone")
zones = (df.groupby("zone_basic")
           .agg(attempts=("made", "size"), makes=("made", "sum"), points=("points", "sum"))
           .assign(fg_pct=lambda d: (d["makes"] / d["attempts"]).round(3),
                   points_per_shot=lambda d: (d["points"] / d["attempts"]).round(2))
           .drop(columns=["points"]).sort_values("attempts", ascending=False))
st.dataframe(zones)