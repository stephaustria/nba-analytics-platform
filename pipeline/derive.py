"""Usage:
    python -m pipeline.derive                      # all seasons in the DB
    python -m pipeline.derive --seasons 2025-26
"""
import argparse
import logging

import numpy as np
import pandas as pd
from sqlalchemy import text

from analytics import metrics
from app.db import SessionLocal, engine
from app.models import PlayerSeasonAdvanced, TeamSeasonAdvanced
from pipeline.ingest import records, upsert

log = logging.getLogger("derive")


def load(sql: str) -> pd.DataFrame:
    with engine.connect() as conn:
        return pd.read_sql(text(sql), conn)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seasons", nargs="+")
    args = parser.parse_args()

    pgs = load("SELECT pgs.*, g.season, g.season_type FROM player_game_stats pgs "
               "JOIN games g ON g.id = pgs.game_id")
    tgs = load("SELECT tgs.*, g.season, g.season_type FROM team_game_stats tgs "
               "JOIN games g ON g.id = tgs.game_id")
    if args.seasons:
        pgs, tgs = pgs[pgs["season"].isin(args.seasons)], tgs[tgs["season"].isin(args.seasons)]

    players = metrics.player_advanced(pgs, tgs).replace([np.inf, -np.inf], np.nan)
    teams = metrics.team_advanced(tgs).replace([np.inf, -np.inf], np.nan)

    with SessionLocal() as session:
        upsert(session, PlayerSeasonAdvanced, records(players), ["player_id", "season", "season_type"])
        upsert(session, TeamSeasonAdvanced, records(teams), ["team_id", "season", "season_type"])
        session.commit()
    log.info("stored %d player-season rows and %d team-season rows", len(players), len(teams))


if __name__ == "__main__":
    main()
