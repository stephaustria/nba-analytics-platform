import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models
from app.db import Base, get_db
from app.main import app


@pytest.fixture()
def client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

    with Session() as s:
        s.add_all([
            models.Team(id=1610612747, abbreviation="LAL", full_name="Los Angeles Lakers",
                        nickname="Lakers", city="Los Angeles", state="California", year_founded=1947),
            models.Team(id=1610612738, abbreviation="BOS", full_name="Boston Celtics",
                        nickname="Celtics", city="Boston", state="Massachusetts", year_founded=1946),
            models.Player(id=2544, full_name="LeBron James", first_name="LeBron",
                          last_name="James", is_active=True),
        ])
        s.commit()

    def override():
        with Session() as s:
            yield s

    app.dependency_overrides[get_db] = override
    yield TestClient(app)
    app.dependency_overrides.clear()
    