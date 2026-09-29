"""Usage:
    python -m pipeline.ingest --seasons 2023-24 2024-25 2025-26
    python -m pipeline.ingest                # refresh the latest season only
"""
import argparse
import logging
import time
from datetime import date

from nba_api.stats.endpoints import leaguegamelog
from nba_api.stats.static import players as static_players
from nba_api.stats.static import teams as static_teams
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from app.db import SessionLocal
from app.models import Game, Player, PlayerGameStat, Team, TeamGameStat

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("ingest")

SEASON_TYPES = ["Regular Season", "Playoffs"]
STAT_MAP = {
    "MIN": "minutes", "FGM": "fgm", "FGA": "fga", "FG3M": "fg3m", "FG3A": "fg3a",
    "FTM": "ftm", "FTA": "fta", "OREB": "oreb", "DREB": "dreb", "REB": "reb",
    "AST": "ast", "STL": "stl", "BLK": "blk", "TOV": "tov", "PF": "pf",
    "PTS": "pts", "PLUS_MINUS": "plus_minus",
}
FLOAT_COLS = {"minutes", "plus_minus"}


# ---------- helpers ----------
def current_season() -> str:
    today = date.today()
    start = today.year if today.month >= 10 else today.year - 1
    return f"{start}-{str(start + 1)[-2:]}"


def records(df) -> list[dict]:
    return df.astype(object).where(df.notna(), None).to_dict("records")


def stats(row: dict) -> dict:
    out = {}
    for src, dst in STAT_MAP.items():
        v = row.get(src)
        out[dst] = None if v is None else (float(v) if dst in FLOAT_COLS else int(v))
    return out


def fetch(season: str, season_type: str, kind: str) -> list[dict]:
    """kind: 'T' for team rows, 'P' for player rows. Retries with backoff."""
    for attempt in range(1, 5):
        try:
            time.sleep(1)  # be polite to the API
            df = leaguegamelog.LeagueGameLog(
                season=season,
                season_type_all_star=season_type,
                player_or_team_abbreviation=kind,
                timeout=60,
            ).get_data_frames()[0]
            return records(df)
        except Exception as exc:
            if attempt == 4:
                raise
            wait = 3 * 2 ** attempt
            log.warning("fetch failed (%s); retrying in %ss", exc, wait)
            time.sleep(wait)


def upsert(session, model, rows: list[dict], keys: list[str]) -> None:
    """Insert or update rows so re-running the pipeline never duplicates data."""
    if not rows:
        return
    insert = pg_insert if session.bind.dialect.name == "postgresql" else sqlite_insert
    for i in range(0, len(rows), 1000):
        chunk = rows[i : i + 1000]
        stmt = insert(model)
        update = {c.name: stmt.excluded[c.name] for c in model.__table__.columns if c.name not in keys}
        stmt = stmt.on_conflict_do_update(index_elements=keys, set_=update)
        session.execute(stmt, chunk)


# ---------- loaders ----------
def load_reference(session) -> None:
    upsert(session, Team, static_teams.get_teams(), ["id"])
    upsert(session, Player, static_players.get_players(), ["id"])
    session.commit()
    log.info("loaded teams and players")


def load_season(session, season: str, season_type: str) -> None:
    team_rows = fetch(season, season_type, "T")
    if not team_rows:
        log.info("%s %s: no games yet", season, season_type)
        return

    games, team_stats = {}, []
    for r in team_rows:
        g = games.setdefault(r["GAME_ID"], {
            "id": r["GAME_ID"], "season": season, "season_type": season_type,
            "game_date": date.fromisoformat(str(r["GAME_DATE"])[:10]),
        })
        side = "home" if " vs. " in r["MATCHUP"] else "away"
        g[f"{side}_team_id"] = r["TEAM_ID"]
        g[f"{side}_score"] = r["PTS"]
        team_stats.append({
            "game_id": r["GAME_ID"], "team_id": r["TEAM_ID"],
            "is_home": side == "home", "wl": r["WL"], **stats(r),
        })

    game_rows = [g for g in games.values() if "home_team_id" in g and "away_team_id" in g]
    valid = {g["id"] for g in game_rows}
    upsert(session, Game, game_rows, ["id"])
    upsert(session, TeamGameStat, [t for t in team_stats if t["game_id"] in valid], ["game_id", "team_id"])

    player_rows = [r for r in fetch(season, season_type, "P") if r["GAME_ID"] in valid]
    known = set(session.scalars(select(Player.id)))
    missing = {r["PLAYER_ID"]: r["PLAYER_NAME"] for r in player_rows if r["PLAYER_ID"] not in known}
    upsert(session, Player, [{"id": i, "full_name": n, "is_active": False} for i, n in missing.items()], ["id"])
    upsert(session, PlayerGameStat, [
        {"game_id": r["GAME_ID"], "player_id": r["PLAYER_ID"], "team_id": r["TEAM_ID"], **stats(r)}
        for r in player_rows
    ], ["game_id", "player_id"])

    session.commit()
    log.info("%s %s: %d games, %d player rows", season, season_type, len(game_rows), len(player_rows))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seasons", nargs="+", default=[current_season()])
    parser.add_argument("--skip-reference", action="store_true")
    args = parser.parse_args()

    with SessionLocal() as session:
        if not args.skip_reference:
            load_reference(session)
        for season in args.seasons:
            for season_type in SEASON_TYPES:
                load_season(session, season, season_type)


if __name__ == "__main__":
    main()
    