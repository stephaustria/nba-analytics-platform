import pandas as pd
import pytest

from analytics import metrics as m


def test_true_shooting():
    assert m.true_shooting(30, 20, 10) == pytest.approx(30 / 48.8)


def test_effective_fg():
    assert m.effective_fg(10, 4, 20) == pytest.approx(0.6)


def test_zero_attempts_is_nan():
    assert pd.isna(m.true_shooting(0, 0, 0))


def _team_row(team_id, wl, pts, fga, fta, oreb, tov):
    return dict(game_id="g1", team_id=team_id, season="2025-26", season_type="Regular Season",
                wl=wl, minutes=240, pts=pts, fgm=35, fga=fga, fg3m=10, fta=fta, ftm=15,
                oreb=oreb, dreb=30, tov=tov)


def test_team_ratings_are_symmetric():
    tgs = pd.DataFrame([_team_row(1, "W", 100, 80, 20, 10, 12),
                        _team_row(2, "L", 95, 85, 15, 8, 14)])
    out = m.team_advanced(tgs).set_index("team_id")
    poss = ((80 + 0.44 * 20 - 10 + 12) + (85 + 0.44 * 15 - 8 + 14)) / 2  # 94.2
    assert out.loc[1, "pace"] == pytest.approx(poss, abs=1e-3)
    assert out.loc[1, "off_rtg"] == pytest.approx(100 * 100 / poss, abs=1e-3)
    assert out.loc[1, "net_rtg"] == pytest.approx(-out.loc[2, "net_rtg"], abs=1e-3)
    assert out.loc[1, "wins"] == 1 and out.loc[2, "losses"] == 1


def test_player_ts_usage_and_rebound_rate():
    tgs = pd.DataFrame([
        dict(game_id="g1", team_id=1, minutes=240, fgm=40, fga=90, fta=25, tov=12, reb=45),
        dict(game_id="g1", team_id=2, minutes=240, fgm=38, fga=88, fta=20, tov=10, reb=40),
    ])
    pgs = pd.DataFrame([dict(
        game_id="g1", player_id=7, team_id=1, season="2025-26", season_type="Regular Season",
        minutes=36, fgm=10, fga=20, fg3m=3, ftm=8, fta=10, oreb=1, dreb=6, reb=7,
        ast=5, stl=1, blk=0, tov=4, pf=2, pts=31)])
    row = m.player_advanced(pgs, tgs).iloc[0]
    assert row["ts_pct"] == pytest.approx(31 / (2 * (20 + 4.4)), abs=1e-3)
    usg = 100 * ((20 + 0.44 * 10 + 4) * 48) / (36 * (90 + 0.44 * 25 + 12))
    assert row["usg_pct"] == pytest.approx(usg, abs=1e-2)
    assert row["reb_pct"] == pytest.approx(100 * 7 * 48 / (36 * (45 + 40)), abs=1e-2)
    