from datetime import date

from pydantic import BaseModel, ConfigDict


class TeamOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    abbreviation: str
    full_name: str
    nickname: str
    city: str
    state: str | None = None
    year_founded: int | None = None


class PlayerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    full_name: str
    first_name: str | None = None
    last_name: str | None = None
    is_active: bool


class GameOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    season: str
    season_type: str
    game_date: date
    home_team_id: int
    away_team_id: int
    home_score: int | None = None
    away_score: int | None = None


class SeasonAverages(BaseModel):
    season: str
    season_type: str
    games_played: int
    mpg: float | None
    ppg: float | None
    rpg: float | None
    apg: float | None
    spg: float | None
    bpg: float | None
    fg_pct: float | None
    fg3_pct: float | None
    ft_pct: float | None
    