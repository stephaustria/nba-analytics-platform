import plotly.express as px
import streamlit as st

import queries as q

st.set_page_config(page_title="Advanced Stats", page_icon="🏀", layout="wide")
st.title("Advanced Stats")

season = st.sidebar.selectbox("Season", q.seasons())
tab_players, tab_teams = st.tabs(["Players", "Teams"])

with tab_players:
    min_minutes = st.slider("Minimum total minutes", 0, 3000, 800, step=100)
    df = q.player_advanced(season, min_minutes)
    if df.empty:
        st.info("No data. Run `python -m pipeline.derive` first, or lower the minutes filter.")
    else:
        st.plotly_chart(px.scatter(
            df, x="usg_pct", y="ts_pct", size="minutes", hover_name="player",
            hover_data=["gp", "game_score", "pts_per36"],
            labels={"usg_pct": "Usage rate (%)", "ts_pct": "True shooting %"},
            title="Efficiency vs. volume (bubble size = minutes played)",
        ))
        st.dataframe(df, hide_index=True, height=500)

with tab_teams:
    teams = q.team_advanced(season)
    if teams.empty:
        st.info("No data. Run `python -m pipeline.derive` first.")
    else:
        fig = px.scatter(
            teams, x="off_rtg", y="def_rtg", text="abbreviation", hover_name="team",
            labels={"off_rtg": "Offensive rating", "def_rtg": "Defensive rating (lower is better)"},
            title="Offense vs. defense",
        )
        fig.update_traces(textposition="top center")
        fig.update_yaxes(autorange="reversed")  # good defense at the top
        st.plotly_chart(fig)
        st.subheader("Ratings and the Four Factors")
        st.dataframe(teams.drop(columns=["abbreviation"]), hide_index=True, height=600)
        st.caption("Four Factors: eFG%, turnover %, offensive rebound %, and free throw rate, "
                   "shown for the team (offense) and its opponents (defense).")