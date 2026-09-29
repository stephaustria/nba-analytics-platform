from fastapi import APIRouter, HTTPException, Query
from app.services import nba_client

router = APIRouter(prefix="/players", tags=["players"])


@router.get("")
def list_players(
    search: str | None = Query(None, description="Full or partial player name"),
    active_only: bool = False,
    limit: int = Query(50, le=500),
):
    return nba_client.list_players(search, active_only)[:limit]


@router.get("/{player_id}")
def get_player(player_id: int):
    player = nba_client.get_player(player_id)
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    return player


@router.get("/{player_id}/career")
def get_career(player_id: int):
    if not nba_client.get_player(player_id):
        raise HTTPException(status_code=404, detail="Player not found")
    return nba_client.get_player_career(player_id)
