from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Game
from app.schemas import GameOut

router = APIRouter(prefix="/games", tags=["games"])


@router.get("", response_model=list[GameOut])
def list_games(
    season: str | None = None,
    team_id: int | None = None,
    limit: int = Query(50, le=500),
    db: Session = Depends(get_db),
):
    q = select(Game).order_by(Game.game_date.desc())
    if season:
        q = q.where(Game.season == season)
    if team_id:
        q = q.where(or_(Game.home_team_id == team_id, Game.away_team_id == team_id))
    return db.scalars(q.limit(limit)).all()


@router.get("/{game_id}", response_model=GameOut)
def get_game(game_id: str, db: Session = Depends(get_db)):
    game = db.get(Game, game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    return game