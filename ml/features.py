import numpy as np
import pandas as pd

from analytics.metrics import possessions
from ml.elo import compute_elo

FORM = ["net_rtg", "off_rtg", "def_rtg", "efg", "tov_pct", "orb_pct", "ft_rate", "win", "pace"]
GAME_FORM = [c for c in FORM if c != "pace"]
TEAM_FEATS = ([f"{c}_last10" for c in GAME_FORM] + [f"{c}_szn" for c in GAME_FORM]
              + ["rest_days", "b2b"])
FEATURES = [f"d_{c}" for c in TEAM_FEATS] + ["elo_diff"]  # d_ = home minus away

PLAYER_STATS = ["pts", "reb", "ast", "minutes", "fga"]
OPP_COLS = ["pace_last10", "pace_szn", "def_rtg_last10", "def_rtg_szn", "net_rtg_szn"]
PLAYER_FEATURES = (
    [f"{c}_{w}" for c in PLAYER_STATS for w in ("last5", "last10", "szn")]
    + ["is_home", "rest_days", "b2b", "tm_pace_last10", "tm_net_rtg_szn"]
    + [f"opp_{c}" for c in OPP_COLS]
)


def season_for(d) -> str:
    d = pd.Timestamp(d)
    start = d.year if d.month >= 10 else d.year - 1
    return f"{start}-{str(start + 1)[-2:]}"


def rolling_mean(df: pd.DataFrame, keys: list[str], col: str,
                 window: int | None = None, min_periods: int = 5) -> pd.Series:
    """Mean of PREVIOUS games only (shift(1)), within each group. window=None means
    season-to-date. The current game's own value never enters its features."""
    shifted = df.groupby(keys)[col].shift(1)
    grouped = shifted.groupby([df[k] for k in keys])
    roll = grouped.rolling(window, min_periods=min_periods) if window else grouped.expanding(min_periods=min_periods)
    return roll.mean().reset_index(level=list(range(len(keys))), drop=True)


# ---------------------------------------------------------------- teams
def team_frame(tg: pd.DataFrame) -> pd.DataFrame:
    """One row per team-game with pre-game rolling form and rest days."""
    tg = tg.sort_values(["team_id", "game_date", "game_id"]).reset_index(drop=True)
    o_cols = ["pts", "fgm", "fga", "fg3m", "fta", "ftm", "oreb", "dreb", "tov"]
    opp = tg[["game_id", "team_id"] + o_cols].rename(
        columns={"team_id": "opp_team_id", **{c: f"o_{c}" for c in o_cols}})
    tg = tg.merge(opp, on=["game_id", "opp_team_id"], how="left")

    poss = (possessions(tg["fga"], tg["fta"], tg["oreb"], tg["tov"])
            + possessions(tg["o_fga"], tg["o_fta"], tg["o_oreb"], tg["o_tov"])) / 2
    tg["off_rtg"] = 100 * tg["pts"] / poss
    tg["def_rtg"] = 100 * tg["o_pts"] / poss
    tg["net_rtg"] = tg["off_rtg"] - tg["def_rtg"]
    tg["pace"] = 48 * poss / (tg["minutes"] / 5)
    tg["efg"] = (tg["fgm"] + 0.5 * tg["fg3m"]) / tg["fga"]
    tg["tov_pct"] = tg["tov"] / (tg["fga"] + 0.44 * tg["fta"] + tg["tov"])
    tg["orb_pct"] = tg["oreb"] / (tg["oreb"] + tg["o_dreb"])
    tg["ft_rate"] = tg["ftm"] / tg["fga"]
    tg["win"] = (tg["wl"] == "W").astype(float).where(tg["wl"].notna())

    keys = ["team_id", "season"]
    for c in FORM:
        tg[f"{c}_last10"] = rolling_mean(tg, keys, c, window=10)
        tg[f"{c}_szn"] = rolling_mean(tg, keys, c)

    prev = tg.groupby("team_id")["game_date"].shift(1)
    tg["rest_days"] = (tg["game_date"] - prev).dt.days.clip(upper=7).fillna(7)
    tg["b2b"] = (tg["rest_days"] == 1).astype(int)
    return tg


def game_table(tg: pd.DataFrame, games: pd.DataFrame) -> pd.DataFrame:
    """One row per game: home-minus-away features, Elo, and the label (NaN if unplayed)."""
    tf = team_frame(tg)
    home = tf[tf["is_home"]].set_index("game_id")
    away = tf[~tf["is_home"]].set_index("game_id")
    idx = home.index.intersection(away.index)
    h, a = home.loc[idx], away.loc[idx]
    elo = compute_elo(games).set_index("game_id").loc[idx]
    res = games.set_index("game_id").loc[idx]

    out = pd.DataFrame({"game_date": h["game_date"], "season": h["season"],
                        "home_team_id": h["team_id"], "away_team_id": a["team_id"]})
    for c in TEAM_FEATS:
        out[f"d_{c}"] = h[c] - a[c]
    out["elo_home"], out["elo_away"] = elo["elo_home"], elo["elo_away"]
    out["elo_diff"] = out["elo_home"] - out["elo_away"]
    out["home_net_rtg_last10"], out["away_net_rtg_last10"] = h["net_rtg_last10"], a["net_rtg_last10"]
    out["home_rest_days"], out["away_rest_days"] = h["rest_days"], a["rest_days"]
    played = res["home_score"].notna() & res["away_score"].notna()
    out["home_win"] = (res["home_score"] > res["away_score"]).astype(float).where(played)
    return out.reset_index()


def placeholder_frames(home_id: int, away_id: int, game_date) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Rows for a game that hasn't happened, so the normal feature code can score it."""
    d, season = pd.Timestamp(game_date), season_for(game_date)
    tg = pd.DataFrame([
        dict(game_id="FUTURE", team_id=home_id, opp_team_id=away_id, is_home=True, season=season, game_date=d),
        dict(game_id="FUTURE", team_id=away_id, opp_team_id=home_id, is_home=False, season=season, game_date=d),
    ])
    games = pd.DataFrame([dict(game_id="FUTURE", game_date=d, season=season, home_team_id=home_id,
                               away_team_id=away_id, home_score=np.nan, away_score=np.nan)])
    return tg, games


# -------------------------------------------------------------- players
def player_frame(pg: pd.DataFrame) -> pd.DataFrame:
    """One row per player-game with pre-game rolling averages and rest days."""
    pg = pg.sort_values(["player_id", "game_date", "game_id"]).reset_index(drop=True)
    keys = ["player_id", "season"]
    for c in PLAYER_STATS:
        pg[f"{c}_last5"] = rolling_mean(pg, keys, c, window=5, min_periods=3)
        pg[f"{c}_last10"] = rolling_mean(pg, keys, c, window=10)
        pg[f"{c}_szn"] = rolling_mean(pg, keys, c)
    prev = pg.groupby("player_id")["game_date"].shift(1)
    pg["rest_days"] = (pg["game_date"] - prev).dt.days.clip(upper=7).fillna(7)
    pg["b2b"] = (pg["rest_days"] == 1).astype(int)
    pg["is_home"] = pg["is_home"].astype(int)
    return pg


def add_team_context(pf: pd.DataFrame, tf: pd.DataFrame) -> pd.DataFrame:
    """Attach the opponent's and the player's own team's pre-game form."""
    opp = tf[["game_id", "team_id"] + OPP_COLS].rename(
        columns={"team_id": "opp_team_id", **{c: f"opp_{c}" for c in OPP_COLS}})
    tm = tf[["game_id", "team_id", "pace_last10", "net_rtg_szn"]].rename(
        columns={"pace_last10": "tm_pace_last10", "net_rtg_szn": "tm_net_rtg_szn"})
    return (pf.merge(opp, on=["game_id", "opp_team_id"], how="left")
              .merge(tm, on=["game_id", "team_id"], how="left"))