import os
from contextlib import contextmanager

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app

test_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSession = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_token(client):
    resp = client.post("/api/auth/register", json={"email": "test@example.com", "password": "testpass123"})
    assert resp.status_code == 200
    return resp.json()["access_token"]


CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "Example_Review_Comparison.csv")


@contextmanager
def count_queries():
    """Context manager that counts SQL queries executed on test_engine."""
    queries = []

    def _listener(_conn, _cursor, statement, _params, _context, _executemany):
        queries.append(statement)

    event.listen(test_engine, "before_cursor_execute", _listener)
    try:
        yield queries
    finally:
        event.remove(test_engine, "before_cursor_execute", _listener)
