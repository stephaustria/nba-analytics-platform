import pandas as pd
from sqlalchemy import text

from app.db import engine


def _read(sql: str, **params) -> pd.DataFrame:
    with engine.connect() as conn:
        return pd.read_sql(text(sql), conn, params=params)


def load_team_games(season_type: str = "Regular Season") -> pd.DataFrame:
    df = _read("""
        SELECT tgs.game_id, tgs.team_id, tgs.is_home, tgs.wl, tgs.minutes, tgs.pts, tgs.fgm,
               tgs.fga, tgs.fg3m, tgs.fta, tgs.ftm, tgs.oreb, tgs.dreb, tgs.tov,
               g.season, g.game_date,
               CASE WHEN tgs.is_home THEN g.away_team_id ELSE g.home_team_id END AS opp_team_id
        FROM team_game_stats tgs JOIN games g ON g.id = tgs.game_id
        WHERE g.season_type = :st
    """, st=season_type)
    df["game_date"] = pd.to_datetime(df["game_date"])
    df["is_home"] = df["is_home"].astype(bool)
    return df


def load_games(season_type: str = "Regular Season") -> pd.DataFrame:
    df = _read("""
        SELECT id AS game_id, game_date, season, home_team_id, away_team_id, home_score, away_score
        FROM games WHERE season_type = :st
    """, st=season_type)
    df["game_date"] = pd.to_datetime(df["game_date"])
    return df


def load_player_games(season_type: str = "Regular Season") -> pd.DataFrame:
    df = _read("""
        SELECT pgs.game_id, pgs.player_id, pgs.team_id, pgs.minutes, pgs.pts, pgs.reb, pgs.ast,
               pgs.fga, g.season, g.game_date,
               CASE WHEN g.home_team_id = pgs.team_id THEN 1 ELSE 0 END AS is_home,
               CASE WHEN g.home_team_id = pgs.team_id THEN g.away_team_id ELSE g.home_team_id END AS opp_team_id
        FROM player_game_stats pgs JOIN games g ON g.id = pgs.game_id
        WHERE g.season_type = :st AND pgs.minutes > 0
    """, st=season_type)
    df["game_date"] = pd.to_datetime(df["game_date"])
    df["is_home"] = df["is_home"].astype(bool)
    return df