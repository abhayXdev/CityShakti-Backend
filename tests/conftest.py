import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import models
from database import Base, get_db
from main import app

# Use in-memory SQLite for testing to ensure isolation and speed
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


# Override the application's dependency to use the test database
app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="function")
def test_db():
    # Patch the background task DB session imports
    import routes.complaints

    routes.complaints.SessionLocal = TestingSessionLocal

    # Create the database schema before each test
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    yield db
    db.close()
    # Drop the database schema after each test to ensure a clean state
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function", autouse=True)
def reset_rate_limiter():
    from rate_limiter import limiter

    limiter._storage.reset()


@pytest.fixture(scope="function")
def client(test_db):
    # The test_db fixture is requested to ensure the database is initialized
    with TestClient(app) as c:
        yield c
