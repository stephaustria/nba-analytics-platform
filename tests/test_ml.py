import numpy as np
import pandas as pd
import pytest

from ml.elo import compute_elo
from ml.features import FEATURES, game_table, placeholder_frames, player_frame


def synthetic(n_games: int = 14, seed: int = 0):
    """Two teams playing each other repeatedly, alternating home court."""
    rng = np.random.default_rng(seed)
    tg_rows, game_rows = [], []
    for i in range(n_games):
        home, away = (1, 2) if i % 2 == 0 else (2, 1)
        date = pd.Timestamp("2025-11-01") + pd.Timedelta(days=2 * i)
        score = {home: int(rng.integers(95, 125)), away: int(rng.integers(95, 125))}
        for team, opp, is_home in ((home, away, True), (away, home, False)):
            tg_rows.append(dict(
                game_id=f"g{i:02d}", team_id=team, opp_team_id=opp, is_home=is_home,
                wl="W" if score[team] > score[opp] else "L", season="2025-26", game_date=date,
                minutes=240, pts=score[team], fgm=int(rng.integers(35, 45)),
                fga=int(rng.integers(85, 95)), fg3m=int(rng.integers(10, 16)),
                fta=int(rng.integers(18, 28)), ftm=int(rng.integers(14, 22)),
                oreb=int(rng.integers(8, 13)), dreb=int(rng.integers(30, 36)),
                tov=int(rng.integers(11, 17))))
        game_rows.append(dict(game_id=f"g{i:02d}", game_date=date, season="2025-26",
                              home_team_id=home, away_team_id=away,
                              home_score=score[home], away_score=score[away]))
    return pd.DataFrame(tg_rows), pd.DataFrame(game_rows)


def test_features_ignore_the_game_itself():
    tg, games = synthetic()
    before = game_table(tg, games).set_index("game_id").loc["g13", FEATURES].astype(float)
    assert before.notna().all()

    tg2, games2 = tg.copy(), games.copy()
    tg2.loc[tg2["game_id"] == "g13", "pts"] = 200          # change the game's own result
    games2.loc[games2["game_id"] == "g13", "home_score"] = 200
    after = game_table(tg2, games2).set_index("game_id").loc["g13", FEATURES].astype(float)
    np.testing.assert_allclose(before.to_numpy(), after.to_numpy())


def test_future_game_gets_features_but_no_label():
    tg, games = synthetic()
    ph_tg, ph_games = placeholder_frames(1, 2, "2025-12-15")
    table = game_table(pd.concat([tg, ph_tg], ignore_index=True),
                       pd.concat([games, ph_games], ignore_index=True))
    row = table[table["game_id"] == "FUTURE"].iloc[0]
    assert row[FEATURES].astype(float).notna().all()
    assert pd.isna(row["home_win"])


def test_elo_starts_even_and_moves_after_a_result():
    _, games = synthetic()
    elo = compute_elo(games).set_index("game_id")
    assert elo.loc["g00", "elo_home"] == 1500 and elo.loc["g00", "elo_away"] == 1500
    first = games.iloc[0]
    team1_won = first["home_score"] > first["away_score"]
    assert (elo.loc["g01", "elo_away"] > 1500) == team1_won  # team 1 is the away side in g01


def test_player_rolling_uses_only_past_games():
    pg = pd.DataFrame({
        "game_id": [f"g{i}" for i in range(8)], "player_id": 7, "season": "2025-26",
        "game_date": pd.date_range("2025-11-01", periods=8, freq="2D"),
        "pts": [10, 20, 30, 40, 50, 60, 70, 80], "reb": 1, "ast": 1, "minutes": 30, "fga": 10,
        "team_id": 1, "opp_team_id": 2, "is_home": True,
    })
    out = player_frame(pg).set_index("game_id")
    assert out.loc["g6", "pts_last5"] == pytest.approx(np.mean([20, 30, 40, 50, 60]))
    assert np.isnan(out.loc["g0", "pts_last5"])