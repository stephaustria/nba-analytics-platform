def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_list_teams(client):
    r = client.get("/teams")
    assert r.status_code == 200
    assert len(r.json()) == 2


def test_unknown_team_404(client):
    assert client.get("/teams/999").status_code == 404


def test_player_search(client):
    r = client.get("/players", params={"search": "lebron"})
    assert r.status_code == 200
    assert r.json()[0]["full_name"] == "LeBron James"


def test_unknown_player_404(client):
    assert client.get("/players/999999999").status_code == 404


def test_career_empty_for_player_without_games(client):
    assert client.get("/players/2544/career").json() == []


def test_games_empty(client):
    assert client.get("/games").json() == []