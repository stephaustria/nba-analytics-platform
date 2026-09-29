import functools
import time
from pathlib import Path

import joblib
import pandas as pd

from ml.data import load_games, load_player_games, load_team_games
from ml.features import (add_team_context, game_table, placeholder_frames, player_frame,
                         season_for, team_frame)

MODEL_DIR = Path("models")
_cache: dict = {}


class ModelNotTrained(RuntimeError):
    pass


class NotEnoughData(ValueError):
    pass


@functools.lru_cache(maxsize=4)
def _load(path: str, mtime: float):
    return joblib.load(path)


def load_bundle(kind: str) -> dict:
    path = MODEL_DIR / f"{kind}_model.joblib"
    if not path.exists():
        raise ModelNotTrained(f"No {kind} model found. Run `python -m ml.train_{kind}_model` first.")
    return _load(str(path), path.stat().st_mtime)


def _cached(name: str, loader, ttl: int = 600):
    hit = _cache.get(name)
    if hit and time.time() - hit[0] < ttl:
        return hit[1]
    value = loader()
    _cache[name] = (time.time(), value)
    return value


def predict_game(home_team_id: int, away_team_id: int, game_date) -> dict:
    bundle = load_bundle("game")
    d = pd.Timestamp(game_date)
    tg, games = _cached("tg", load_team_games), _cached("games", load_games)
    tg, games = tg[tg["game_date"] < d], games[games["game_date"] < d]  # only the past
    ph_tg, ph_games = placeholder_frames(home_team_id, away_team_id, d)

    table = game_table(pd.concat([tg, ph_tg], ignore_index=True),
                       pd.concat([games, ph_games], ignore_index=True))
    row = table[table["game_id"] == "FUTURE"].iloc[0]
    X = row[bundle["features"]].astype(float).to_frame().T
    if X.isna().to_numpy().any():
        raise NotEnoughData("Each team needs at least 5 games earlier in that season "
                            "before the model can make a prediction.")

    p_home = float(bundle["model"].predict_proba(X)[0, 1])
    return {
        "home_team_id": home_team_id, "away_team_id": away_team_id, "game_date": d.date(),
        "home_win_prob": round(p_home, 4), "away_win_prob": round(1 - p_home, 4),
        "predicted_winner_id": home_team_id if p_home >= 0.5 else away_team_id,
        "elo_home": round(float(row["elo_home"]), 1), "elo_away": round(float(row["elo_away"]), 1),
        "home_last10_net_rtg": round(float(row["home_net_rtg_last10"]), 2),
        "away_last10_net_rtg": round(float(row["away_net_rtg_last10"]), 2),
        "home_rest_days": int(row["home_rest_days"]), "away_rest_days": int(row["away_rest_days"]),
        "model": bundle["name"], "trained_through": bundle["trained_through"],
    }


def predict_player(player_id: int, opponent_id: int, is_home: bool, game_date) -> dict:
    bundle = load_bundle("player")
    d, season = pd.Timestamp(game_date), season_for(game_date)
    pg, tg = _cached("pg", load_player_games), _cached("tg", load_team_games)

    hist = pg[(pg["player_id"] == player_id) & (pg["game_date"] < d)]
    if hist.empty:
        raise NotEnoughData("No games found for this player before that date.")
    last = hist.sort_values("game_date").iloc[-1]
    if (d - last["game_date"]).days > 400:
        raise NotEnoughData("This player has no recent games.")
    team_id = int(last["team_id"])

    home_id, away_id = (team_id, opponent_id) if is_home else (opponent_id, team_id)
    ph_tg, _ = placeholder_frames(home_id, away_id, d)
    season_tg = tg[(tg["season"] == season) & (tg["game_date"] < d)]  # form resets each season
    tf = team_frame(pd.concat([season_tg, ph_tg], ignore_index=True))

    ph = pd.DataFrame([dict(game_id="FUTURE", player_id=player_id, team_id=team_id,
                            opp_team_id=opponent_id, is_home=bool(is_home), season=season, game_date=d)])
    pf = add_team_context(player_frame(pd.concat([hist, ph], ignore_index=True)), tf)
    row = pf[pf["game_id"] == "FUTURE"].iloc[0]
    if row[["pts_szn", "minutes_last10", "opp_def_rtg_szn"]].isna().any():
        raise NotEnoughData("The player and the opponent each need at least 5 games earlier in "
                            "that season before the model can make a prediction.")

    X = row[bundle["features"]].astype(float).to_frame().T
    out = {"player_id": player_id, "team_id": team_id, "opponent_id": opponent_id,
           "is_home": bool(is_home), "game_date": d.date(), "trained_through": bundle["trained_through"]}
    for target, models in bundle["models"].items():
        mean = max(float(models["mean"].predict(X)[0]), 0.0)
        low = min(max(float(models["low"].predict(X)[0]), 0.0), mean)
        high = max(float(models["high"].predict(X)[0]), mean)
        out[target] = {"prediction": round(mean, 1), "low": round(low, 1), "high": round(high, 1)}
    return out