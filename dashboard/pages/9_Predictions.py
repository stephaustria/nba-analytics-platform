import json
from pathlib import Path

import pandas as pd
import streamlit as st

import queries as q
from ml import predict

st.set_page_config(page_title="Predictions", page_icon="🏀", layout="wide")
st.title("Predictions")
st.caption("The models only see games before the chosen date, so pick a past date to backtest "
           "them against what actually happened.")

seasons = q.seasons()
default_date = q.games_list(seasons[0]).iloc[0]["game_date"].date()  # most recent game in the DB
teams = q.teams()
team_names = dict(zip(teams["id"], teams["full_name"]))

tab_game, tab_player, tab_report = st.tabs(["Game outcome", "Player stat line", "Model report"])

with tab_game:
    c1, c2, c3 = st.columns(3)
    home = c1.selectbox("Home team", list(team_names), format_func=team_names.get, index=None, key="g_home")
    away = c2.selectbox("Away team", list(team_names), format_func=team_names.get, index=None, key="g_away")
    when = c3.date_input("Game date", value=default_date, key="g_date")
    if st.button("Predict game") and home is not None and away is not None:
        try:
            p = predict.predict_game(int(home), int(away), when)
        except (predict.ModelNotTrained, predict.NotEnoughData, ValueError) as exc:
            st.error(str(exc))
        else:
            a, b = st.columns(2)
            a.metric(f"{team_names[home]} (home)", f"{p['home_win_prob']:.1%}")
            b.metric(team_names[away], f"{p['away_win_prob']:.1%}")
            st.progress(p["home_win_prob"])
            st.dataframe(pd.DataFrame({
                "Elo": [p["elo_home"], p["elo_away"]],
                "Net rating, last 10": [p["home_last10_net_rtg"], p["away_last10_net_rtg"]],
                "Days of rest": [p["home_rest_days"], p["away_rest_days"]],
            }, index=[team_names[home], team_names[away]]))
            st.caption(f"Model: {p['model']}, trained through {p['trained_through']}.")

with tab_player:
    players = q.players_with_stats()
    player_names = dict(zip(players["id"], players["full_name"]))
    c1, c2, c3, c4 = st.columns([3, 3, 1, 2])
    pid = c1.selectbox("Player", list(player_names), format_func=player_names.get,
                       index=None, placeholder="Start typing a name...", key="p_player")
    opp = c2.selectbox("Opponent", list(team_names), format_func=team_names.get, index=None, key="p_opp")
    at_home = c3.checkbox("Home", value=True)
    when_p = c4.date_input("Game date", value=default_date, key="p_date")
    if st.button("Predict stat line") and pid is not None and opp is not None:
        try:
            p = predict.predict_player(int(pid), int(opp), at_home, when_p)
        except (predict.ModelNotTrained, predict.NotEnoughData, ValueError) as exc:
            st.error(str(exc))
        else:
            cols = st.columns(3)
            for col, key, label in zip(cols, ("pts", "reb", "ast"), ("Points", "Rebounds", "Assists")):
                col.metric(label, p[key]["prediction"])
                col.caption(f"80% range: {p[key]['low']} to {p[key]['high']}")
            st.caption("Assumes the player plays. The models don't know about injuries or rest days off.")

with tab_report:
    for kind in ("game", "player"):
        path = Path("models") / f"{kind}_model_metrics.json"
        st.subheader(f"{kind.capitalize()} model")
        if path.exists():
            report = json.loads(path.read_text())
            st.dataframe(pd.DataFrame(report["summary"]).T)
            st.caption(f"Trained through {report['trained_through']}.")
        else:
            st.info(f"Run `python -m ml.train_{kind}_model` to create this report.")