"""Tests for news application service."""

from unittest.mock import MagicMock

from app.services.news_service import NewsApplicationService
from app.tasks.news.collector import NewsCollector
from app.tasks.news.exceptions import NewsFeedError
from app.tasks.news.models import NewsItem

SAMPLE_RSS = """<?xml version="1.0"?><rss><channel>
<item><title>A</title><link>https://example.com/a</link><description>a</description></item>
<item><title>B</title><link>https://example.com/b</link><description>b</description></item>
</channel></rss>"""


def _item(url: str, title: str) -> NewsItem:
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    return NewsItem(
        title=title,
        url=url,
        summary="s",
        source="Mock",
        published_at=now,
        collected_at=now,
    )


def test_refresh_inserts_new_items(db_session):
    collector = NewsCollector()
    items = collector.parse_feed_content(SAMPLE_RSS, "Mock")
    mock_collector = MagicMock()
    mock_collector.fetch_feed.return_value = items

    service = NewsApplicationService(db_session, collector=mock_collector)
    service._feeds = [{"name": "Mock", "url": "http://mock/feed"}]

    result = service.refresh()
    assert result.inserted_count == 2
    assert result.skipped_duplicates == 0
    assert not result.errors
    assert len(result.new_items) == 2

    meta = service.get_refresh_metadata()
    assert meta["last_refresh_at"] is not None
    assert meta["last_inserted_count"] == 2
    assert meta["last_warning_count"] == 0


def test_refresh_skips_duplicates(db_session):
    collector = NewsCollector()
    items = collector.parse_feed_content(SAMPLE_RSS, "Mock")
    mock_collector = MagicMock()
    mock_collector.fetch_feed.return_value = items

    service = NewsApplicationService(db_session, collector=mock_collector)
    service._feeds = [{"name": "Mock", "url": "http://mock/feed"}]

    service.refresh()
    result = service.refresh()
    assert result.inserted_count == 0
    assert result.skipped_duplicates == 2


def test_refresh_continues_when_one_feed_fails(db_session):
    mock_collector = MagicMock()
    mock_collector.fetch_feed.side_effect = [
        NewsFeedError("broken"),
        [_item("https://example.com/ok", "OK")],
    ]

    service = NewsApplicationService(db_session, collector=mock_collector)
    service._feeds = [
        {"name": "Bad", "url": "http://bad"},
        {"name": "Good", "url": "http://good"},
    ]

    result = service.refresh()
    assert result.inserted_count == 1
    assert len(result.errors) == 1
    assert result.errors[0]["source"] == "Bad"
