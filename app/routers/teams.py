from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Game, Player, Team
from app.models import PlayerGameStat as PGS
from app.schemas import PlayerOut, TeamOut

router = APIRouter(prefix="/teams", tags=["teams"])


@router.get("", response_model=list[TeamOut])
def list_teams(db: Session = Depends(get_db)):
    return db.scalars(select(Team).order_by(Team.full_name)).all()


@router.get("/{team_id}", response_model=TeamOut)
def get_team(team_id: int, db: Session = Depends(get_db)):
    team = db.get(Team, team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    return team


@router.get("/{team_id}/roster", response_model=list[PlayerOut])
def get_roster(team_id: int, season: str = "2025-26", db: Session = Depends(get_db)):
    """Players who appeared in a game for this team that season."""
    if not db.get(Team, team_id):
        raise HTTPException(status_code=404, detail="Team not found")
    ids = (
        select(PGS.player_id)
        .join(Game, Game.id == PGS.game_id)
        .where(PGS.team_id == team_id, Game.season == season)
        .distinct()
    )
    return db.scalars(select(Player).where(Player.id.in_(ids)).order_by(Player.full_name)).all()