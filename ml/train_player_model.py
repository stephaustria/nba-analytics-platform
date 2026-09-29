"""Usage: python -m ml.train_player_model"""
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error

from ml.data import load_player_games, load_team_games
from ml.features import PLAYER_FEATURES, add_team_context, player_frame, team_frame

MODEL_DIR = Path("models")
TARGETS = ["pts", "reb", "ast"]
PARAMS = dict(max_iter=300, learning_rate=0.05, max_leaf_nodes=15, min_samples_leaf=100,
              l2_regularization=1.0, random_state=0)


def fit_target(train: pd.DataFrame, target: str) -> dict:
    X, y = train[PLAYER_FEATURES], train[target]
    return {
        "mean": HistGradientBoostingRegressor(**PARAMS).fit(X, y),
        "low": HistGradientBoostingRegressor(loss="quantile", quantile=0.1, **PARAMS).fit(X, y),
        "high": HistGradientBoostingRegressor(loss="quantile", quantile=0.9, **PARAMS).fit(X, y),
    }


def main() -> None:
    tf = team_frame(load_team_games())
    df = add_team_context(player_frame(load_player_games()), tf)
    df = df[(df["minutes_last10"] >= 12) & df["pts_szn"].notna()]  # rotation players with history

    test_season = sorted(df["season"].unique())[-1]
    train, test = df[df["season"] < test_season], df[df["season"] == test_season]
    print(f"Train: {len(train):,} player-games   Test ({test_season}): {len(test):,}")

    rows = []
    for t in TARGETS:
        m = fit_target(train, t)
        pred = m["mean"].predict(test[PLAYER_FEATURES])
        lo, hi = m["low"].predict(test[PLAYER_FEATURES]), m["high"].predict(test[PLAYER_FEATURES])
        rows.append({
            "target": t,
            "mae_season_avg": mean_absolute_error(test[t], test[f"{t}_szn"]),
            "mae_last10_avg": mean_absolute_error(test[t], test[f"{t}_last10"].fillna(test[f"{t}_szn"])),
            "mae_model": mean_absolute_error(test[t], pred),
            "range_coverage": float(((test[t] >= lo) & (test[t] <= hi)).mean()),
        })
    report = pd.DataFrame(rows).set_index("target").round(3)
    print("\nMean absolute error on held-out season (lower is better):")
    print(report.to_string())
    print("\nrange_coverage should be close to 0.80 (share of games inside the 10th-90th percentile range).")

    final = {t: fit_target(df, t) for t in TARGETS}  # final models use every season
    MODEL_DIR.mkdir(exist_ok=True)
    trained_through = str(df["game_date"].max().date())
    joblib.dump({"models": final, "features": PLAYER_FEATURES, "trained_through": trained_through},
                MODEL_DIR / "player_model.joblib")
    (MODEL_DIR / "player_model_metrics.json").write_text(json.dumps(
        {"test_season": test_season, "trained_through": trained_through,
         "summary": report.to_dict("index")}, indent=2))
    print(f"\nSaved models/player_model.joblib (trained through {trained_through})")


if __name__ == "__main__":
    main()