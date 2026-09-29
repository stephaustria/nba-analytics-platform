import pandas as pd
from nba_api.stats.static import players, teams
from nba_api.stats.endpoints import playercareerstats, commonteamroster


def _clean(df: pd.DataFrame) -> list[dict]:
    """Convert a DataFrame to JSON-safe records (NaN -> None)."""
    return df.astype(object).where(df.notna(), None).to_dict(orient="records")


def list_players(search: str | None = None, active_only: bool = False) -> list[dict]:
    results = players.find_players_by_full_name(search) if search else players.get_players()
    if active_only:
        results = [p for p in results if p["is_active"]]
    return results


def get_player(player_id: int) -> dict | None:
    return players.find_player_by_id(player_id)


def get_player_career(player_id: int) -> list[dict]:
    df = playercareerstats.PlayerCareerStats(player_id=player_id, timeout=30).get_data_frames()[0]
    return _clean(df)


def list_teams() -> list[dict]:
    return teams.get_teams()


def get_team(team_id: int) -> dict | None:
    return teams.find_team_name_by_id(team_id)


def get_team_roster(team_id: int, season: str | None = None) -> list[dict]:
    kwargs = {"team_id": team_id, "timeout": 30}
    if season:
        kwargs["season"] = season  # e.g. "2025-26"
    df = commonteamroster.CommonTeamRoster(**kwargs).get_data_frames()[0]
    return _clean(df)
