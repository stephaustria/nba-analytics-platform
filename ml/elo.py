import pandas as pd


def compute_elo(games: pd.DataFrame, k: float = 20.0, home_adv: float = 70.0,
                carry: float = 0.75, base: float = 1500.0) -> pd.DataFrame:
    """Pre-game Elo for every game. Games with missing scores (future games) get ratings
    but do not update anything."""
    ratings, last_season, rows = {}, {}, []
    for g in games.sort_values(["game_date", "game_id"]).itertuples(index=False):
        for team in (g.home_team_id, g.away_team_id):
            if team not in ratings:
                ratings[team] = base
            elif last_season[team] != g.season:  # first game of a new season
                ratings[team] = base + carry * (ratings[team] - base)
            last_season[team] = g.season

        eh, ea = ratings[g.home_team_id], ratings[g.away_team_id]
        rows.append((g.game_id, eh, ea))
        if pd.isna(g.home_score) or pd.isna(g.away_score):
            continue

        margin = g.home_score - g.away_score
        diff = eh + home_adv - ea
        expected = 1 / (1 + 10 ** (-diff / 400))
        winner_diff = diff if margin > 0 else -diff
        mult = (abs(margin) + 3) ** 0.8 / (7.5 + 0.006 * winner_diff)
        delta = k * mult * ((1.0 if margin > 0 else 0.0) - expected)
        ratings[g.home_team_id] += delta
        ratings[g.away_team_id] -= delta
    return pd.DataFrame(rows, columns=["game_id", "elo_home", "elo_away"])