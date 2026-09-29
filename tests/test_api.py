from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_teams_returns_30():
    r = client.get("/teams")
    assert r.status_code == 200
    assert len(r.json()) == 30


def test_player_search():
    r = client.get("/players", params={"search": "lebron"})
    assert r.status_code == 200
    assert any(p["full_name"] == "LeBron James" for p in r.json())


def test_unknown_player_404():
    assert client.get("/players/999999999").status_code == 404
    