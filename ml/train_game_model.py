"""Usage: python -m ml.train_game_model"""
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, brier_score_loss, log_loss
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from ml.data import load_games, load_team_games
from ml.features import FEATURES, game_table

MODEL_DIR = Path("models")


def make_models() -> dict:
    return {
        "elo_only": (make_pipeline(StandardScaler(), LogisticRegression()), ["elo_diff"]),
        "logistic": (make_pipeline(StandardScaler(), LogisticRegression(C=0.3, max_iter=2000)), FEATURES),
        "grad_boost": (HistGradientBoostingClassifier(max_depth=3, learning_rate=0.05, max_iter=200,
                                                      l2_regularization=1.0, random_state=0), FEATURES),
    }


def score(y, p) -> dict:
    return {"accuracy": accuracy_score(y, p > 0.5), "log_loss": log_loss(y, p),
            "brier": brier_score_loss(y, p)}


def calibration(y, p, bins: int = 10) -> pd.DataFrame:
    df = pd.DataFrame({"p": p, "y": y})
    df["bin"] = pd.cut(df["p"], np.linspace(0, 1, bins + 1))
    return (df.groupby("bin", observed=True)
              .agg(games=("y", "size"), predicted=("p", "mean"), actual=("y", "mean")).round(3))


def main() -> None:
    table = game_table(load_team_games(), load_games())
    table = table.dropna(subset=FEATURES + ["home_win"]).sort_values("game_date")
    seasons = sorted(table["season"].unique())
    table = table[table["season"] != seasons[0]]  # first season only warms up Elo
    seasons = seasons[1:]

    test_seasons = [s for s in seasons[-3:] if (table["season"] < s).sum() >= 1500]
    if not test_seasons:
        print("Not enough history. Ingest more seasons first (see Step 2).")
        return

    rows, last_fold_preds = [], {}
    for season in test_seasons:
        train, test = table[table["season"] < season], table[table["season"] == season]
        y_test = test["home_win"]

        base = np.full(len(test), train["home_win"].mean())
        rows.append({"model": "home_baseline", "season": season, **score(y_test, base)})
        for name, (model, feats) in make_models().items():
            model.fit(train[feats], train["home_win"])
            p = model.predict_proba(test[feats])[:, 1]
            rows.append({"model": name, "season": season, **score(y_test, p)})
            last_fold_preds[name] = (y_test.to_numpy(), p)

    results = pd.DataFrame(rows)
    summary = results.groupby("model")[["accuracy", "log_loss", "brier"]].mean().round(4)
    print(f"\nWalk-forward results, test seasons {test_seasons} (mean across folds):")
    print(summary.sort_values("log_loss").to_string())

    best = summary.drop(index="home_baseline")["log_loss"].idxmin()
    print(f"\nBest model by log loss: {best}")
    print(f"\nCalibration of {best} on {test_seasons[-1]}:")
    print(calibration(*last_fold_preds[best]).to_string())

    model, feats = make_models()[best]
    model.fit(table[feats], table["home_win"])  # final model uses every season
    MODEL_DIR.mkdir(exist_ok=True)
    trained_through = str(table["game_date"].max().date())
    joblib.dump({"name": best, "model": model, "features": feats,
                 "trained_through": trained_through}, MODEL_DIR / "game_model.joblib")
    (MODEL_DIR / "game_model_metrics.json").write_text(json.dumps(
        {"best_model": best, "trained_through": trained_through, "test_seasons": test_seasons,
         "summary": summary.to_dict("index")}, indent=2))
    print(f"\nSaved models/game_model.joblib (trained through {trained_through})")


if __name__ == "__main__":
    main()