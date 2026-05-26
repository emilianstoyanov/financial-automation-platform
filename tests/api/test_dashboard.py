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
    assert "health-scheduler-block" in body
    assert "updateSchedulerStatus" in body
    assert "formatSchedulerInterval" in body
    assert "scheduler disabled · manual refresh only" in body
    assert "scheduler enabled ·" in body
    assert '"News"' in body or "News scheduler" in body
    assert '"Rates"' in body or "Rates scheduler" in body
    assert "Financial Rates / Exchange History" in body
    assert "rates-refresh" in body
    assert "rates-load" in body
    assert "refreshRates" in body
    assert "loadRatesList" in body
    assert "resetRatesTask" in body
    assert 'id="rates-clear"' in body
    assert "Task 5" in body
    assert "Financial News" in body
    assert "news-sources-line" in body
    assert "news-source-badge" in body
    assert "news-source-badge--bnb" in body
    assert "news-source-badge--investor-bg" in body
    assert "news-source-badge--capital" in body
    assert "json-output-toggle" in body
    assert "buildJsonOutputBlock" in body
    assert "BNB" in body
    assert "Investor.bg" in body
    assert "Capital" in body
    assert "news-refresh" in body
    assert "news-cards-grid" in body
    assert "news-article-card" in body
    assert "formatNewsDateTime" in body
    assert "friendlyFeedWarning" in body
    assert "friendlyScrapeUrlError" in body
    assert "Invalid or unreachable URL. Please check the address and try again." in body
    assert "buildNewsLastUpdatedWarningSummary" in body
    assert "newsWarningToggleBadge" in body
    assert "news-warning-toggle" in body
    assert "setNewsWarningHintVisible" in body
    assert "news-last-updated-hint" in body
    assert "buildNewsRefreshStatusLine" in body


def test_dashboard_news_refresh_friendly_messages(client):
    """Dashboard shows friendly feed warnings, not raw parser errors."""
    body = client.get("/").text
    assert "Refresh completed:" in body
    assert "feed warning." in body
    assert (
        "RSS feed could not be parsed. Other feeds were processed successfully."
        in body
    )
    assert "Feed warnings" in body
    assert "news-last-updated-bar" in body
    assert "news-last-updated-hint" in body
    assert 'id="news-last-updated-time"' in body
    assert "news-meta-stat" in body
    assert "updateNewsLastUpdatedPanel" in body
    assert "loadNewsLastUpdated" in body
    assert "Inserted 0, skipped" not in body
    assert "feed error(s)" not in body
    assert "not well-formed (invalid token)" not in body
    assert "Broken feed for BNB" not in body
    assert "health-response-toggle" in body
    assert "View health response" in body
    assert "/api/v1" in body
    assert "result-panel" in body
    assert "llm-file" in body
    assert "drag and drop" in body
    assert "etl-file-zone" in body
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
    assert "news-article-card" in response.text
    assert "news-article-excerpt" in response.text
    assert "news-last-updated-bar" in response.text
    assert "news-sources-line" in response.text
    assert "news-source-badge" in response.text
    assert "json-output-toggle" in response.text
    assert ".news-source-badge--bnb" in response.text
    assert "status-scheduler-dot" in response.text
    assert "rates-last-updated-bar" in response.text
    assert "rates-table" in response.text


def test_dashboard_favicon(client):
    """Favicon PNG is served from /static."""
    response = client.get("/static/favicon.png")
    assert response.status_code == 200
    assert response.headers.get("content-type", "").startswith("image/")
    assert len(response.content) > 0
