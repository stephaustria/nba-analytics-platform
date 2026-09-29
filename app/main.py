from fastapi import FastAPI
from app.routers import players, teams

app = FastAPI(title="NBA Analytics Platform", version="0.1.0")
app.include_router(players.router)
app.include_router(teams.router)


@app.get("/health")
def health():
    return {"status": "ok"}