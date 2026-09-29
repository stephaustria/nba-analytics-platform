from datetime import date

from sqlalchemy import Boolean, Date, Float, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Team(Base):
    __tablename__ = "teams"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    abbreviation: Mapped[str] = mapped_column(String(5))
    full_name: Mapped[str] = mapped_column(String(100))
    nickname: Mapped[str] = mapped_column(String(50))
    city: Mapped[str] = mapped_column(String(50))
    state: Mapped[str | None] = mapped_column(String(50))
    year_founded: Mapped[int | None] = mapped_column(Integer)


class Player(Base):
    __tablename__ = "players"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    full_name: Mapped[str] = mapped_column(String(100), index=True)
    first_name: Mapped[str | None] = mapped_column(String(50))
    last_name: Mapped[str | None] = mapped_column(String(50))
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)


class Game(Base):
    __tablename__ = "games"
    id: Mapped[str] = mapped_column(String(10), primary_key=True)
    season: Mapped[str] = mapped_column(String(7), index=True)       # e.g. "2025-26"
    season_type: Mapped[str] = mapped_column(String(20))             # Regular Season / Playoffs
    game_date: Mapped[date] = mapped_column(Date, index=True)
    home_team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"))
    away_team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"))
    home_score: Mapped[int | None] = mapped_column(Integer)
    away_score: Mapped[int | None] = mapped_column(Integer)


class BoxScoreMixin:
    minutes: Mapped[float | None] = mapped_column(Float)
    fgm: Mapped[int | None] = mapped_column(Integer)
    fga: Mapped[int | None] = mapped_column(Integer)
    fg3m: Mapped[int | None] = mapped_column(Integer)
    fg3a: Mapped[int | None] = mapped_column(Integer)
    ftm: Mapped[int | None] = mapped_column(Integer)
    fta: Mapped[int | None] = mapped_column(Integer)
    oreb: Mapped[int | None] = mapped_column(Integer)
    dreb: Mapped[int | None] = mapped_column(Integer)
    reb: Mapped[int | None] = mapped_column(Integer)
    ast: Mapped[int | None] = mapped_column(Integer)
    stl: Mapped[int | None] = mapped_column(Integer)
    blk: Mapped[int | None] = mapped_column(Integer)
    tov: Mapped[int | None] = mapped_column(Integer)
    pf: Mapped[int | None] = mapped_column(Integer)
    pts: Mapped[int | None] = mapped_column(Integer)
    plus_minus: Mapped[float | None] = mapped_column(Float)


class TeamGameStat(BoxScoreMixin, Base):
    __tablename__ = "team_game_stats"
    game_id: Mapped[str] = mapped_column(ForeignKey("games.id"), primary_key=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), primary_key=True)
    is_home: Mapped[bool] = mapped_column(Boolean)
    wl: Mapped[str | None] = mapped_column(String(1))


class PlayerGameStat(BoxScoreMixin, Base):
    __tablename__ = "player_game_stats"
    game_id: Mapped[str] = mapped_column(ForeignKey("games.id"), primary_key=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"), primary_key=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"))

    __table_args__ = (Index("ix_pgs_player", "player_id"), Index("ix_pgs_team", "team_id"))