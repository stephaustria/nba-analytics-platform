"""Usage:
    python -m pipeline.lineups --seasons 2024-25 2025-26
"""
import argparse
import logging

from nba_api.stats.endpoints import leaguedashlineups

from app.db import SessionLocal
from app.models import LineupStat
from pipeline.ingest import SEASON_TYPES, current_season, records, upsert
from pipeline.util import retry

log = logging.getLogger("lineups")


def load(session, season: str, season_type: str, size: int) -> None:
    df = retry(lambda: leaguedashlineups.LeagueDashLineups(
        group_quantity=size, measure_type_detailed_defense="Advanced",
        per_mode_detailed="Totals", season=season, season_type_all_star=season_type, timeout=60,
    ).get_data_frames()[0])
    rows = [{
        "group_id": r["GROUP_ID"], "team_id": int(r["TEAM_ID"]), "season": season,
        "season_type": season_type, "group_quantity": size, "group_name": r["GROUP_NAME"],
        "gp": r.get("GP"), "wins": r.get("W"), "losses": r.get("L"), "minutes": r.get("MIN"),
        "off_rating": r.get("OFF_RATING"), "def_rating": r.get("DEF_RATING"),
        "net_rating": r.get("NET_RATING"), "pace": r.get("PACE"),
    } for r in records(df)]
    upsert(session, LineupStat, rows, ["group_id", "team_id", "season", "season_type", "group_quantity"])
    session.commit()
    log.info("%s %s (%d-man): %d lineups", season, season_type, size, len(rows))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seasons", nargs="+", default=[current_season()])
    parser.add_argument("--sizes", nargs="+", type=int, default=[5, 2])
    args = parser.parse_args()
    with SessionLocal() as session:
        for season in args.seasons:
            for season_type in SEASON_TYPES:
                for size in args.sizes:
                    load(session, season, season_type, size)


if __name__ == "__main__":
    main()