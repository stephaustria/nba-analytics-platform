from fastapi import FastAPI

from app.routers import games, players, predict, teams

app = FastAPI(title="NBA Analytics Platform", version="0.5.0")
app.include_router(players.router)
app.include_router(teams.router)
app.include_router(games.router)
app.include_router(predict.router)


@app.get("/health")
def health():
    return {"status": "ok"}