import sys
from decimal import Decimal
from pathlib import Path

# Make the project root importable so we can reuse app/db.py
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import streamlit as st
from sqlalchemy import text

from app.db import engine

STAT_COLS = {"Points": "pts", "Rebounds": "reb", "Assists": "ast", "Steals": "stl", "Blocks": "blk"}


# ---------- helpers ----------
def _run(sql: str, **params) -> pd.DataFrame:
    with engine.connect() as conn:
        df = pd.read_sql(text(sql), conn, params=params)
    for col in df.columns:  # PostgreSQL returns AVG() as Decimal
        if df[col].map(lambda v: isinstance(v, Decimal)).any():
            df[col] = df[col].astype(float)
    if "game_date" in df.columns:
        df["game_date"] = pd.to_datetime(df["game_date"])
    return df


def _ratio(n, d):
    return (n / d.where(d > 0)).round(3)


def add_pcts(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["fg_pct"] = _ratio(df["fgm"], df["fga"])
    df["fg3_pct"] = _ratio(df["fg3m"], df["fg3a"])
    df["ft_pct"] = _ratio(df["ftm"], df["fta"])
    return df


# ---------- lookups ----------
@st.cache_data(ttl=600)
def seasons() -> list[str]:
    return _run("SELECT DISTINCT season FROM games ORDER BY season DESC")["season"].tolist()


@st.cache_data(ttl=600)
def teams() -> pd.DataFrame:
    return _run("SELECT id, full_name, abbreviation FROM teams ORDER BY full_name")


@st.cache_data(ttl=600)
def players_with_stats() -> pd.DataFrame:
    return _run("""
        SELECT p.id, p.full_name FROM players p
        WHERE p.id IN (SELECT DISTINCT player_id FROM player_game_stats)
        ORDER BY p.full_name
    """)


# ---------- league ----------
@st.cache_data(ttl=600)
def standings(season: str) -> pd.DataFrame:
    df = _run("""
        SELECT t.id, t.full_name, t.abbreviation,
               COUNT(*) AS gp,
               SUM(CASE WHEN tgs.wl = 'W' THEN 1 ELSE 0 END) AS wins,
               SUM(CASE WHEN tgs.wl = 'L' THEN 1 ELSE 0 END) AS losses,
               AVG(tgs.pts) AS ppg,
               AVG(tgs.plus_minus) AS margin
        FROM team_game_stats tgs
        JOIN games g ON g.id = tgs.game_id
        JOIN teams t ON t.id = tgs.team_id
        WHERE g.season = :season AND g.season_type = 'Regular Season'
        GROUP BY t.id, t.full_name, t.abbreviation
    """, season=season)
    df["win_pct"] = (df["wins"] / df["gp"]).round(3)
    df["ppg"] = df["ppg"].round(1)
    df["margin"] = df["margin"].round(1)
    return df.sort_values(["win_pct", "margin"], ascending=False).reset_index(drop=True)


@st.cache_data(ttl=600)
def leaders(season: str, stat_label: str, min_games: int) -> pd.DataFrame:
    col = STAT_COLS[stat_label]  # whitelisted, so safe to place in the SQL
    df = _run(f"""
        SELECT p.full_name AS player, COUNT(*) AS gp, AVG(pgs.{col}) AS per_game
        FROM player_game_stats pgs
        JOIN games g ON g.id = pgs.game_id
        JOIN players p ON p.id = pgs.player_id
        WHERE g.season = :season AND g.season_type = 'Regular Season'
        GROUP BY p.id, p.full_name
        HAVING COUNT(*) >= :min_games
        ORDER BY per_game DESC
        LIMIT 10
    """, season=season, min_games=min_games)
    df["per_game"] = df["per_game"].round(1)
    return df


# ---------- players ----------
@st.cache_data(ttl=600)
def player_seasons(pid: int) -> pd.DataFrame:
    df = _run("""
        SELECT g.season, g.season_type, COUNT(*) AS gp,
               AVG(pgs.minutes) AS mpg, AVG(pgs.pts) AS ppg, AVG(pgs.reb) AS rpg,
               AVG(pgs.ast) AS apg, AVG(pgs.stl) AS spg, AVG(pgs.blk) AS bpg,
               AVG(pgs.tov) AS topg,
               SUM(pgs.fgm) AS fgm, SUM(pgs.fga) AS fga,
               SUM(pgs.fg3m) AS fg3m, SUM(pgs.fg3a) AS fg3a,
               SUM(pgs.ftm) AS ftm, SUM(pgs.fta) AS fta
        FROM player_game_stats pgs
        JOIN games g ON g.id = pgs.game_id
        WHERE pgs.player_id = :pid
        GROUP BY g.season, g.season_type
        ORDER BY g.season, g.season_type
    """, pid=pid)
    df = add_pcts(df)
    avg_cols = ["mpg", "ppg", "rpg", "apg", "spg", "bpg", "topg"]
    df[avg_cols] = df[avg_cols].round(1)
    return df


@st.cache_data(ttl=600)
def player_log(pid: int, season: str) -> pd.DataFrame:
    df = _run("""
        SELECT g.game_date, g.season_type,
               CASE WHEN g.home_team_id = pgs.team_id THEN 'vs' ELSE '@' END AS venue,
               opp.abbreviation AS opp,
               pgs.minutes, pgs.pts, pgs.reb, pgs.ast, pgs.stl, pgs.blk, pgs.tov,
               pgs.fgm, pgs.fga, pgs.fg3m, pgs.fg3a, pgs.ftm, pgs.fta, pgs.plus_minus,
               CASE WHEN g.home_team_id = pgs.team_id
                    THEN g.home_score - g.away_score
                    ELSE g.away_score - g.home_score END AS margin
        FROM player_game_stats pgs
        JOIN games g ON g.id = pgs.game_id
        JOIN teams opp ON opp.id = CASE WHEN g.home_team_id = pgs.team_id
                                        THEN g.away_team_id ELSE g.home_team_id END
        WHERE pgs.player_id = :pid AND g.season = :season
        ORDER BY g.game_date
    """, pid=pid, season=season)
    df["result"] = df["margin"].apply(lambda m: "W" if m > 0 else "L")
    return df


# ---------- teams ----------
@st.cache_data(ttl=600)
def team_games(tid: int, season: str) -> pd.DataFrame:
    return _run("""
        SELECT g.game_date, g.season_type,
               CASE WHEN tgs.is_home THEN 'vs' ELSE '@' END AS venue,
               opp.abbreviation AS opp, tgs.wl, tgs.pts,
               CASE WHEN tgs.is_home THEN g.away_score ELSE g.home_score END AS opp_pts,
               tgs.plus_minus AS margin
        FROM team_game_stats tgs
        JOIN games g ON g.id = tgs.game_id
        JOIN teams opp ON opp.id = CASE WHEN tgs.is_home THEN g.away_team_id ELSE g.home_team_id END
        WHERE tgs.team_id = :tid AND g.season = :season
        ORDER BY g.game_date
    """, tid=tid, season=season)


@st.cache_data(ttl=600)
def team_players(tid: int, season: str) -> pd.DataFrame:
    df = _run("""
        SELECT p.full_name AS player, COUNT(*) AS gp,
               AVG(pgs.minutes) AS mpg, AVG(pgs.pts) AS ppg, AVG(pgs.reb) AS rpg, AVG(pgs.ast) AS apg,
               SUM(pgs.fgm) AS fgm, SUM(pgs.fga) AS fga,
               SUM(pgs.fg3m) AS fg3m, SUM(pgs.fg3a) AS fg3a,
               SUM(pgs.ftm) AS ftm, SUM(pgs.fta) AS fta
        FROM player_game_stats pgs
        JOIN games g ON g.id = pgs.game_id
        JOIN players p ON p.id = pgs.player_id
        WHERE pgs.team_id = :tid AND g.season = :season AND g.season_type = 'Regular Season'
        GROUP BY p.id, p.full_name
        ORDER BY ppg DESC
    """, tid=tid, season=season)
    df = add_pcts(df).drop(columns=["fgm", "fga", "fg3m", "fg3a", "ftm", "fta", "ft_pct"])
    df[["mpg", "ppg", "rpg", "apg"]] = df[["mpg", "ppg", "rpg", "apg"]].round(1)
    return df


# ---------- games ----------
@st.cache_data(ttl=600)
def games_list(season: str, team_id: int | None = None) -> pd.DataFrame:
    where, params = "g.season = :season", {"season": season}
    if team_id:
        where += " AND (g.home_team_id = :tid OR g.away_team_id = :tid)"
        params["tid"] = team_id
    return _run(f"""
        SELECT g.id, g.game_date, g.season_type,
               a.abbreviation AS away, h.abbreviation AS home,
               g.away_score, g.home_score
        FROM games g
        JOIN teams h ON h.id = g.home_team_id
        JOIN teams a ON a.id = g.away_team_id
        WHERE {where}
        ORDER BY g.game_date DESC, g.id
    """, **params)


@st.cache_data(ttl=600)
def box_score(game_id: str) -> pd.DataFrame:
    return _run("""
        SELECT t.abbreviation AS team, p.full_name AS player, pgs.minutes, pgs.pts, pgs.reb,
               pgs.ast, pgs.stl, pgs.blk, pgs.tov, pgs.fgm, pgs.fga, pgs.fg3m, pgs.fg3a,
               pgs.ftm, pgs.fta, pgs.plus_minus
        FROM player_game_stats pgs
        JOIN players p ON p.id = pgs.player_id
        JOIN teams t ON t.id = pgs.team_id
        WHERE pgs.game_id = :gid
        ORDER BY t.abbreviation, COALESCE(pgs.minutes, 0) DESC
    """, gid=game_id)
