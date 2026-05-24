"""Dashboard UI route tests."""


def test_dashboard_home(client):
    """GET / renders the local dashboard."""
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    body = response.text
    assert "Financial Automation Platform" in body
    assert "ETL Pipeline" in body
    assert "/docs" in body
    assert "System Status" in body
    assert "Task 5" in body
    assert "health-response-toggle" in body
    assert "View health response" in body
    assert "/api/v1" in body
    assert "result-panel" in body
    assert "llm-file" in body
    assert "Upload document" in body
    assert "etl-rejected-toggle" in body
    assert "Data Quality:" in body
    assert 'href="/static/favicon.png"' in body
    assert "dash-file-upload" in body
    assert "btn-clear-results" in body
    assert "Clear results" in body
    assert 'id="etl-clear"' in body
    assert "Advanced AI Settings" in body
    assert 'id="llm-model"' in body
    assert "llm-power-level" in body


def test_dashboard_static_css(client):
    """Dashboard stylesheet is served from /static."""
    response = client.get("/static/css/dashboard.css")
    assert response.status_code == 200
    assert "dashboard-body" in response.text


def test_dashboard_favicon(client):
    """Favicon PNG is served from /static."""
    response = client.get("/static/favicon.png")
    assert response.status_code == 200
    assert response.headers.get("content-type", "").startswith("image/")
    assert len(response.content) > 0
