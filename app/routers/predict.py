from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Player, Team
from ml import predict

router = APIRouter(prefix="/predict", tags=["predictions"])


class GamePrediction(BaseModel):
    home_team_id: int
    away_team_id: int
    game_date: date
    home_win_prob: float
    away_win_prob: float
    predicted_winner_id: int
    elo_home: float
    elo_away: float
    home_last10_net_rtg: float
    away_last10_net_rtg: float
    home_rest_days: int
    away_rest_days: int
    model: str
    trained_through: str


class Interval(BaseModel):
    prediction: float
    low: float
    high: float


class PlayerPrediction(BaseModel):
    player_id: int
    player: str
    team_id: int
    opponent_id: int
    is_home: bool
    game_date: date
    pts: Interval
    reb: Interval
    ast: Interval
    trained_through: str


def _run(fn, *args):
    try:
        return fn(*args)
    except predict.ModelNotTrained as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except predict.NotEnoughData as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.get("/game", response_model=GamePrediction)
def predict_game(home_team_id: int, away_team_id: int, game_date: date, db: Session = Depends(get_db)):
    """Win probability for a game. Only games before `game_date` are used, so past dates work as backtests."""
    if home_team_id == away_team_id:
        raise HTTPException(status_code=422, detail="The two teams must be different")
    for tid in (home_team_id, away_team_id):
        if not db.get(Team, tid):
            raise HTTPException(status_code=404, detail=f"Team {tid} not found")
    return _run(predict.predict_game, home_team_id, away_team_id, game_date)


@router.get("/player/{player_id}", response_model=PlayerPrediction)
def predict_player(player_id: int, opponent_id: int, game_date: date, home: bool = True,
                   db: Session = Depends(get_db)):
    """Points, rebounds, and assists with an 80% range, assuming the player plays."""
    player = db.get(Player, player_id)
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    if not db.get(Team, opponent_id):
        raise HTTPException(status_code=404, detail=f"Team {opponent_id} not found")
    result = _run(predict.predict_player, player_id, opponent_id, home, game_date)
    return {**result, "player": player.full_name}