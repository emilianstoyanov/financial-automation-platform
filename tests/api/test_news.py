"""News API endpoint tests."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from app.core.config import Settings
from app.models.news import NewsArticle
from app.tasks.news.models import NewsItem, RefreshCollectionResult

SINGLE_FEED_SETTINGS = Settings(
    NEWS_SCHEDULER_ENABLED=False,
    NEWS_RSS_FEEDS=[{"name": "Integration", "url": "http://example.com/feed"}],
)

SAMPLE_RSS = """<?xml version="1.0"?><rss><channel>
<item><title>API Headline</title><link>https://example.com/api-1</link>
<description>API summary</description></item>
</channel></rss>"""


def _seed_article(db_session) -> NewsArticle:
    article = NewsArticle(
        title="Stored headline",
        url="https://example.com/stored",
        summary="Stored summary",
        source="Seed",
        published_at=datetime(2024, 2, 1, tzinfo=timezone.utc),
        collected_at=datetime(2024, 2, 2, tzinfo=timezone.utc),
    )
    db_session.add(article)
    db_session.commit()
    db_session.refresh(article)
    return article


def test_get_news_empty(client):
    response = client.get("/api/v1/news?limit=10")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["items"] == []
    assert data["last_refresh_at"] is None


def test_get_news_returns_stored_items(client, db_session):
    _seed_article(db_session)
    response = client.get("/api/v1/news?limit=5")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["title"] == "Stored headline"
    assert data["items"][0]["url"] == "https://example.com/stored"


def test_get_news_sanitizes_html_summary(client, db_session):
    """API returns plain-text summaries without raw HTML markup."""
    article = NewsArticle(
        title="HTML headline",
        url="https://example.com/html-story",
        summary='<img src="x" /><br />Markets &amp; bonds rally',
        source="Capital",
        published_at=datetime(2024, 6, 15, 14, 30, tzinfo=timezone.utc),
        collected_at=datetime(2024, 6, 16, tzinfo=timezone.utc),
    )
    db_session.add(article)
    db_session.commit()

    response = client.get("/api/v1/news?limit=5")
    data = response.json()
    summary = data["items"][0]["summary"]

    assert "<img" not in summary
    assert "<br" not in summary
    assert summary == "Markets & bonds rally"


def test_post_news_refresh_with_mocked_collector(client, db_session):
    from app.tasks.news.collector import NewsCollector

    items = NewsCollector().parse_feed_content(SAMPLE_RSS, "Mock")
    mock_result = RefreshCollectionResult(
        inserted_count=1,
        skipped_duplicates=0,
        errors=[],
        new_items=items,
    )

    with patch(
        "app.api.v1.news.NewsApplicationService.refresh",
        return_value=mock_result,
    ):
        response = client.post("/api/v1/news/refresh")

    assert response.status_code == 200
    data = response.json()
    assert data["inserted_count"] == 1
    assert data["skipped_duplicates"] == 0
    assert len(data["preview"]) == 1
    assert data["preview"][0]["title"] == "API Headline"


def test_post_news_refresh_integration(client, db_session):
    """End-to-end refresh using mocked feedparser network fetch."""
    from app.tasks.news.collector import NewsCollector

    items = NewsCollector().parse_feed_content(SAMPLE_RSS, "Integration")
    mock_collector = MagicMock()
    mock_collector.fetch_feed.return_value = items

    with patch("app.services.news_service.get_settings", return_value=SINGLE_FEED_SETTINGS):
        with patch("app.services.news_service.NewsCollector") as mock_cls:
            mock_cls.return_value = mock_collector
            response = client.post("/api/v1/news/refresh")

    assert response.status_code == 200
    data = response.json()
    assert data["inserted_count"] == 1

    list_response = client.get("/api/v1/news?limit=10")
    list_data = list_response.json()
    assert list_data["total"] == 1
    assert list_data["last_refresh_at"] is not None
    assert list_data["last_inserted_count"] == 1
    assert list_data["last_skipped_duplicates"] == 0
    assert list_data["last_warning_count"] == 0


def test_post_news_refresh_updates_metadata(client, db_session):
    from app.tasks.news.collector import NewsCollector

    items = NewsCollector().parse_feed_content(SAMPLE_RSS, "Mock")
    mock_collector = MagicMock()
    mock_collector.fetch_feed.return_value = items

    with patch("app.services.news_service.get_settings", return_value=SINGLE_FEED_SETTINGS):
        with patch("app.services.news_service.NewsCollector") as mock_cls:
            mock_cls.return_value = mock_collector
            response = client.post("/api/v1/news/refresh")

    assert response.status_code == 200
    data = response.json()
    assert data["last_refresh_at"] is not None
    assert data["last_inserted_count"] == 1
    assert data["last_skipped_duplicates"] == 0
    assert data["last_warning_count"] == 0

    get_response = client.get("/api/v1/news?limit=5")
    get_data = get_response.json()
    assert get_data["last_refresh_at"] is not None
    assert get_data["last_inserted_count"] == 1
    assert get_data["last_warning_count"] == 0
