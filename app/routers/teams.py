from fastapi import APIRouter, HTTPException
from app.services import nba_client

router = APIRouter(prefix="/teams", tags=["teams"])


@router.get("")
def list_teams():
    return nba_client.list_teams()


@router.get("/{team_id}")
def get_team(team_id: int):
    team = nba_client.get_team(team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    return team


@router.get("/{team_id}/roster")
def get_roster(team_id: int, season: str | None = None):
    if not nba_client.get_team(team_id):
        raise HTTPException(status_code=404, detail="Team not found")
    return nba_client.get_team_roster(team_id, season)