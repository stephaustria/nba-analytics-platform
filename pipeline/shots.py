"""Usage:
    python -m pipeline.shots --season 2025-26 --top 100
    python -m pipeline.shots --season 2025-26 --player-id 201939
"""
import argparse
import logging

from nba_api.stats.endpoints import shotchartdetail
from sqlalchemy import select, text

from app.db import SessionLocal
from app.models import Game, Shot
from pipeline.ingest import current_season, records, upsert
from pipeline.util import retry

log = logging.getLogger("shots")


def top_scorers(session, season: str, n: int) -> list[int]:
    rows = session.execute(text("""
        SELECT pgs.player_id
        FROM player_game_stats pgs JOIN games g ON g.id = pgs.game_id
        WHERE g.season = :season AND g.season_type = 'Regular Season'
        GROUP BY pgs.player_id ORDER BY SUM(pgs.pts) DESC LIMIT :n
    """), {"season": season, "n": n})
    return [r[0] for r in rows]


def load_player(session, player_id: int, season: str, season_type: str, known_games: set[str]) -> int:
    df = retry(lambda: shotchartdetail.ShotChartDetail(
        team_id=0, player_id=player_id, season_nullable=season,
        season_type_all_star=season_type, context_measure_simple="FGA", timeout=60,
    ).get_data_frames()[0])
    rows = [{
        "game_id": r["GAME_ID"], "game_event_id": int(r["GAME_EVENT_ID"]),
        "player_id": int(r["PLAYER_ID"]), "team_id": int(r["TEAM_ID"]),
        "season": season, "season_type": season_type, "period": r["PERIOD"],
        "action_type": r["ACTION_TYPE"], "shot_type": r["SHOT_TYPE"],
        "zone_basic": r["SHOT_ZONE_BASIC"], "zone_area": r["SHOT_ZONE_AREA"],
        "zone_range": r["SHOT_ZONE_RANGE"], "distance": r["SHOT_DISTANCE"],
        "loc_x": r["LOC_X"], "loc_y": r["LOC_Y"], "made": int(r["SHOT_MADE_FLAG"]) == 1,
    } for r in records(df) if r["GAME_ID"] in known_games]
    upsert(session, Shot, rows, ["game_id", "game_event_id", "player_id"])
    session.commit()
    return len(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--season", default=current_season())
    parser.add_argument("--season-type", default="Regular Season")
    parser.add_argument("--top", type=int, default=100)
    parser.add_argument("--player-id", type=int, nargs="+")
    args = parser.parse_args()

    with SessionLocal() as session:
        known_games = set(session.scalars(select(Game.id)))
        ids = args.player_id or top_scorers(session, args.season, args.top)
        for i, pid in enumerate(ids, 1):
            n = load_player(session, pid, args.season, args.season_type, known_games)
            log.info("[%d/%d] player %s: %d shots", i, len(ids), pid, n)


if __name__ == "__main__":
    main()