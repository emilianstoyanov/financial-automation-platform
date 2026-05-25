"""Pytest fixtures."""

from unittest.mock import MagicMock, patch

import pytest
import app.models  # noqa: F401 — register ORM models for metadata
from app.main import create_app
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from app.core.database import Base, get_db


@pytest.fixture
def db_engine():
    """In-memory SQLite engine for tests."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session(db_engine):
    """Database session bound to test engine."""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_session):
    """FastAPI test client with overridden database dependency."""
    mock_scheduler = MagicMock()

    with (
        patch("app.main.NewsRefreshScheduler", return_value=mock_scheduler),
        patch("app.main.RatesRefreshScheduler", return_value=mock_scheduler),
    ):
        app = create_app()

        def override_get_db():
            try:
                yield db_session
            finally:
                pass

        app.dependency_overrides[get_db] = override_get_db

        with TestClient(app) as test_client:
            yield test_client

        app.dependency_overrides.clear()
