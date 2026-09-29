import streamlit as st

import queries as q

st.set_page_config(page_title="Games", page_icon="🏀", layout="wide")
st.title("Games")

teams = q.teams()
names = dict(zip(teams["id"], teams["full_name"]))
left, right = st.columns(2)
season = left.selectbox("Season", q.seasons())
tid = right.selectbox("Team (optional)", options=list(names), format_func=names.get,
                      index=None, placeholder="All teams")

games = q.games_list(season, int(tid) if tid is not None else None)
if games.empty:
    st.info("No games found.")
    st.stop()

st.dataframe(games.drop(columns=["id"]), hide_index=True, height=300)

# ---- box score ----
labels = {
    r.id: f"{r.game_date:%b %d, %Y}: {r.away} {r.away_score} @ {r.home} {r.home_score}"
    for r in games.itertuples()
}
game_id = st.selectbox("Box score", options=list(labels), format_func=labels.get)
box = q.box_score(game_id)
for team, grp in box.groupby("team", sort=False):
    st.markdown(f"**{team}**")
    st.dataframe(grp.drop(columns=["team"]), hide_index=True)
    