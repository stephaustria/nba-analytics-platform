import plotly.express as px
import streamlit as st

import queries as q

st.set_page_config(page_title="Lineups", page_icon="🏀", layout="wide")
st.title("Lineups")

teams = q.teams()
names = dict(zip(teams["id"], teams["full_name"]))
c1, c2, c3 = st.columns(3)
season = c1.selectbox("Season", q.seasons())
tid = c2.selectbox("Team", options=list(names), format_func=names.get,
                   index=None, placeholder="Choose a team...")
size = c3.radio("Lineup size", [5, 2], horizontal=True, format_func=lambda n: f"{n}-man")
min_minutes = st.slider("Minimum minutes together", 0, 500, 50, step=10)
if tid is None:
    st.info("Pick a team to get started.")
    st.stop()

df = q.lineups(season, int(tid), size, min_minutes)
if df.empty:
    st.info("No lineups found. Run `python -m pipeline.lineups` or lower the minutes filter.")
    st.stop()

top = df.head(10).sort_values("net_rating")
st.plotly_chart(px.bar(top, x="net_rating", y="lineup", orientation="h",
                       hover_data=["minutes", "off_rating", "def_rating"],
                       labels={"net_rating": "Net rating", "lineup": ""},
                       title=f"Top {size}-man lineups by net rating"))
st.dataframe(df, hide_index=True, height=500)
st.caption("Small minute totals are noisy. Treat lineups with under about 100 minutes together "
           "as suggestive, not conclusive.")