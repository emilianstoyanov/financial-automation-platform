"""Health endpoint tests."""


def test_api_v1_health(client):
    """GET /api/v1/health returns 200 with database connected."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("healthy", "degraded")
    assert data["database"] == "connected"
    assert data["version"] == "0.1.0"
