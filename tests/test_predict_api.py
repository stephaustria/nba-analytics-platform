from ml import predict

LAL, BOS = 1610612747, 1610612738


def test_unknown_team_404(client):
    r = client.get("/predict/game", params={"home_team_id": 999, "away_team_id": BOS,
                                            "game_date": "2026-01-15"})
    assert r.status_code == 404


def test_same_team_422(client):
    r = client.get("/predict/game", params={"home_team_id": LAL, "away_team_id": LAL,
                                            "game_date": "2026-01-15"})
    assert r.status_code == 422


def test_missing_model_returns_503(client, monkeypatch, tmp_path):
    monkeypatch.setattr(predict, "MODEL_DIR", tmp_path)  # an empty folder, so no model files
    r = client.get("/predict/game", params={"home_team_id": LAL, "away_team_id": BOS,
                                            "game_date": "2026-01-15"})
    assert r.status_code == 503