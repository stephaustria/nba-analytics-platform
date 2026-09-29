import numpy as np
import pandas as pd

KEYS_P = ["player_id", "season", "season_type"]
KEYS_T = ["team_id", "season", "season_type"]
PLAYER_STATS = ["minutes", "fgm", "fga", "fg3m", "ftm", "fta", "oreb", "dreb",
                "reb", "ast", "stl", "blk", "tov", "pf", "pts"]


def div(a, b):
    """Division that returns NaN instead of erroring or returning inf when b == 0."""
    return a / np.where(b == 0, np.nan, b)


def true_shooting(pts, fga, fta):
    return div(pts, 2 * (fga + 0.44 * fta))


def effective_fg(fgm, fg3m, fga):
    return div(fgm + 0.5 * fg3m, fga)


def possessions(fga, fta, oreb, tov):
    return fga + 0.44 * fta - oreb + tov


def game_score(d: pd.DataFrame) -> pd.Series:
    """Hollinger Game Score for each row of a player box-score frame."""
    return (d["pts"] + 0.4 * d["fgm"] - 0.7 * d["fga"] - 0.4 * (d["fta"] - d["ftm"])
            + 0.7 * d["oreb"] + 0.3 * d["dreb"] + d["stl"] + 0.7 * d["ast"]
            + 0.7 * d["blk"] - 0.4 * d["pf"] - d["tov"])


def player_advanced(pgs: pd.DataFrame, tgs: pd.DataFrame) -> pd.DataFrame:
    """One row per player, season, season_type.

    pgs: player_game_stats joined with games (needs season, season_type)
    tgs: team_game_stats for the same games
    """
    pgs = pgs[pgs["minutes"].fillna(0) > 0].copy()
    pgs[PLAYER_STATS] = pgs[PLAYER_STATS].fillna(0)

    tm_cols = ["minutes", "fgm", "fga", "fta", "tov", "reb"]
    tm = tgs[["game_id", "team_id"] + tm_cols].rename(columns={c: f"tm_{c}" for c in tm_cols})
    opp = tgs[["game_id", "team_id", "reb"]].rename(columns={"team_id": "opp_team_id", "reb": "opp_reb"})

    df = pgs.merge(tm, on=["game_id", "team_id"]).merge(opp, on="game_id")
    df = df[df["team_id"] != df["opp_team_id"]].copy()  # keep only the opposing team's row
    df["game_score"] = game_score(df)

    sum_cols = PLAYER_STATS + [f"tm_{c}" for c in tm_cols] + ["opp_reb", "game_score"]
    grouped = df.groupby(KEYS_P)
    s = grouped[sum_cols].sum()
    s["gp"] = grouped.size()
    tm_min5 = s["tm_minutes"] / 5

    out = pd.DataFrame({
        "gp": s["gp"],
        "minutes": s["minutes"],
        "mpg": s["minutes"] / s["gp"],
        "ts_pct": true_shooting(s["pts"], s["fga"], s["fta"]),
        "efg_pct": effective_fg(s["fgm"], s["fg3m"], s["fga"]),
        "usg_pct": 100 * div((s["fga"] + 0.44 * s["fta"] + s["tov"]) * tm_min5,
                             s["minutes"] * (s["tm_fga"] + 0.44 * s["tm_fta"] + s["tm_tov"])),
        "ast_pct": 100 * div(s["ast"], (s["minutes"] / tm_min5) * s["tm_fgm"] - s["fgm"]),
        "reb_pct": 100 * div(s["reb"] * tm_min5, s["minutes"] * (s["tm_reb"] + s["opp_reb"])),
        "tov_pct": 100 * div(s["tov"], s["fga"] + 0.44 * s["fta"] + s["tov"]),
        "game_score": s["game_score"] / s["gp"],
        "pts_per36": 36 * div(s["pts"], s["minutes"]),
        "reb_per36": 36 * div(s["reb"], s["minutes"]),
        "ast_per36": 36 * div(s["ast"], s["minutes"]),
    })
    return out.reset_index().round(4)


def team_advanced(tgs: pd.DataFrame) -> pd.DataFrame:
    """One row per team, season, season_type.

    tgs: team_game_stats joined with games (needs season, season_type)
    """
    cols = ["minutes", "pts", "fgm", "fga", "fg3m", "fta", "ftm", "oreb", "dreb", "tov"]
    t = tgs.copy()
    t["win"] = (t["wl"] == "W").astype(int)
    t[cols] = t[cols].fillna(0)

    o = t[["game_id", "team_id"] + cols].rename(
        columns={"team_id": "opp_team_id", **{c: f"o_{c}" for c in cols}})
    df = t.merge(o, on="game_id")
    df = df[df["team_id"] != df["opp_team_id"]].copy()
    df["poss"] = (possessions(df["fga"], df["fta"], df["oreb"], df["tov"])
                  + possessions(df["o_fga"], df["o_fta"], df["o_oreb"], df["o_tov"])) / 2

    grouped = df.groupby(KEYS_T)
    s = grouped[cols + [f"o_{c}" for c in cols] + ["poss", "win"]].sum()
    s["gp"] = grouped.size()

    out = pd.DataFrame({
        "gp": s["gp"],
        "wins": s["win"],
        "losses": s["gp"] - s["win"],
        "pace": 48 * div(s["poss"], s["minutes"] / 5),
        "off_rtg": 100 * div(s["pts"], s["poss"]),
        "def_rtg": 100 * div(s["o_pts"], s["poss"]),
        "efg_pct": effective_fg(s["fgm"], s["fg3m"], s["fga"]),
        "tov_pct": div(s["tov"], s["fga"] + 0.44 * s["fta"] + s["tov"]),
        "orb_pct": div(s["oreb"], s["oreb"] + s["o_dreb"]),
        "ft_rate": div(s["ftm"], s["fga"]),
        "opp_efg_pct": effective_fg(s["o_fgm"], s["o_fg3m"], s["o_fga"]),
        "opp_tov_pct": div(s["o_tov"], s["o_fga"] + 0.44 * s["o_fta"] + s["o_tov"]),
        "drb_pct": div(s["dreb"], s["dreb"] + s["o_oreb"]),
        "opp_ft_rate": div(s["o_ftm"], s["o_fga"]),
    })
    out["net_rtg"] = out["off_rtg"] - out["def_rtg"]
    return out.reset_index().round(4)
