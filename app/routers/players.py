from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Game, Player
from app.models import PlayerGameStat as PGS
from app.schemas import PlayerOut, SeasonAverages

router = APIRouter(prefix="/players", tags=["players"])


def _pct(made, att):
    return round(made / att, 3) if att else None


def _avg(x):
    return round(x, 1) if x is not None else None


@router.get("", response_model=list[PlayerOut])
def list_players(
    search: str | None = Query(None, description="Full or partial player name"),
    active_only: bool = False,
    limit: int = Query(50, le=500),
    db: Session = Depends(get_db),
):
    q = select(Player).order_by(Player.full_name)
    if search:
        q = q.where(Player.full_name.ilike(f"%{search}%"))
    if active_only:
        q = q.where(Player.is_active.is_(True))
    return db.scalars(q.limit(limit)).all()


@router.get("/{player_id}", response_model=PlayerOut)
def get_player(player_id: int, db: Session = Depends(get_db)):
    player = db.get(Player, player_id)
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    return player


@router.get("/{player_id}/career", response_model=list[SeasonAverages])
def get_career(player_id: int, db: Session = Depends(get_db)):
    if not db.get(Player, player_id):
        raise HTTPException(status_code=404, detail="Player not found")
    rows = db.execute(
        select(
            Game.season, Game.season_type,
            func.count().label("gp"),
            func.avg(PGS.minutes).label("mpg"), func.avg(PGS.pts).label("ppg"),
            func.avg(PGS.reb).label("rpg"), func.avg(PGS.ast).label("apg"),
            func.avg(PGS.stl).label("spg"), func.avg(PGS.blk).label("bpg"),
            func.sum(PGS.fgm).label("fgm"), func.sum(PGS.fga).label("fga"),
            func.sum(PGS.fg3m).label("fg3m"), func.sum(PGS.fg3a).label("fg3a"),
            func.sum(PGS.ftm).label("ftm"), func.sum(PGS.fta).label("fta"),
        )
        .select_from(PGS)
        .join(Game, Game.id == PGS.game_id)
        .where(PGS.player_id == player_id)
        .group_by(Game.season, Game.season_type)
        .order_by(Game.season, Game.season_type)
    ).all()
    return [
        SeasonAverages(
            season=r.season, season_type=r.season_type, games_played=r.gp,
            mpg=_avg(r.mpg), ppg=_avg(r.ppg), rpg=_avg(r.rpg), apg=_avg(r.apg),
            spg=_avg(r.spg), bpg=_avg(r.bpg),
            fg_pct=_pct(r.fgm, r.fga), fg3_pct=_pct(r.fg3m, r.fg3a), ft_pct=_pct(r.ftm, r.fta),
        )
        for r in rows
    ]
