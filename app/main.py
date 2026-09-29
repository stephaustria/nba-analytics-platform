from fastapi import FastAPI

from app.routers import games, players, teams

app = FastAPI(title="NBA Analytics Platform", version="0.2.0")
app.include_router(players.router)
app.include_router(teams.router)
app.include_router(games.router)


@app.get("/health")
def health():
    return {"status": "ok"}