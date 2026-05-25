"""Health endpoint tests."""

from app.api.deps import get_settings_dep
from app.core.config import Settings


def test_api_v1_health(client):
    """GET /api/v1/health returns 200 with database connected."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("healthy", "degraded")
    assert data["database"] == "connected"
    assert data["version"] == "0.1.0"
    assert "news_scheduler_enabled" in data
    assert "news_scheduler_interval_minutes" in data
    assert "rates_scheduler_enabled" in data
    assert "rates_scheduler_interval_minutes" in data
    assert isinstance(data["news_scheduler_enabled"], bool)
    assert isinstance(data["news_scheduler_interval_minutes"], int)
    assert isinstance(data["rates_scheduler_enabled"], bool)
    assert isinstance(data["rates_scheduler_interval_minutes"], int)


def test_health_news_scheduler_settings(client):
    """Health reflects scheduler configuration from settings."""
    settings = Settings(NEWS_SCHEDULER_ENABLED=True, NEWS_SCHEDULER_INTERVAL_MINUTES=60)
    client.app.dependency_overrides[get_settings_dep] = lambda: settings
    try:
        data = client.get("/api/v1/health").json()
        assert data["news_scheduler_enabled"] is True
        assert data["news_scheduler_interval_minutes"] == 60
    finally:
        client.app.dependency_overrides.pop(get_settings_dep, None)


def test_health_news_scheduler_disabled(client):
    settings = Settings(NEWS_SCHEDULER_ENABLED=False, NEWS_SCHEDULER_INTERVAL_MINUTES=1440)
    client.app.dependency_overrides[get_settings_dep] = lambda: settings
    try:
        data = client.get("/api/v1/health").json()
        assert data["news_scheduler_enabled"] is False
        assert data["news_scheduler_interval_minutes"] == 1440
    finally:
        client.app.dependency_overrides.pop(get_settings_dep, None)


def test_health_rates_scheduler_settings(client):
    settings = Settings(RATES_SCHEDULER_ENABLED=True, RATES_SCHEDULER_INTERVAL_MINUTES=720)
    client.app.dependency_overrides[get_settings_dep] = lambda: settings
    try:
        data = client.get("/api/v1/health").json()
        assert data["rates_scheduler_enabled"] is True
        assert data["rates_scheduler_interval_minutes"] == 720
    finally:
        client.app.dependency_overrides.pop(get_settings_dep, None)
