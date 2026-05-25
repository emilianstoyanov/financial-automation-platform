"""Tests for news refresh metadata storage."""

from contextlib import contextmanager
from unittest.mock import MagicMock, patch

from app.repositories.metadata_repository import MetadataRepository
from app.services.news_service import NewsApplicationService
from app.tasks.news.collector import NewsCollector
from app.tasks.news.metadata_keys import (
    NEWS_LAST_INSERTED_COUNT,
    NEWS_LAST_REFRESH_AT,
    NEWS_LAST_WARNING_SUMMARY,
)
from app.tasks.news.exceptions import NewsFeedError
from app.tasks.news.scheduler import NewsRefreshScheduler

SAMPLE_RSS = """<?xml version="1.0"?><rss><channel>
<item><title>Meta</title><link>https://example.com/meta</link><description>x</description></item>
</channel></rss>"""


def test_refresh_persists_metadata(db_session):
    items = NewsCollector().parse_feed_content(SAMPLE_RSS, "Mock")
    mock_collector = MagicMock()
    mock_collector.fetch_feed.return_value = items

    service = NewsApplicationService(db_session, collector=mock_collector)
    service._feeds = [{"name": "Mock", "url": "http://example.com/rss"}]

    service.refresh()
    meta = service.get_refresh_metadata()

    assert meta["last_refresh_at"] is not None
    assert meta["last_inserted_count"] == 1
    assert meta["last_skipped_duplicates"] == 0
    assert meta["last_warning_count"] == 0
    assert meta["last_warning_summary"] is None


def test_refresh_persists_friendly_warning_summary(db_session):
    """Failed feed stores a user-friendly summary, not raw parser text."""
    items = NewsCollector().parse_feed_content(SAMPLE_RSS, "Investor.bg")
    mock_collector = MagicMock()

    def fetch_side_effect(url, source):
        if source == "BNB":
            raise NewsFeedError("not well-formed (invalid token): line 1, column 0")
        return items

    mock_collector.fetch_feed.side_effect = fetch_side_effect

    service = NewsApplicationService(db_session, collector=mock_collector)
    service._feeds = [
        {"name": "BNB", "url": "http://example.com/bnb"},
        {"name": "Investor.bg", "url": "http://example.com/investor"},
    ]

    service.refresh()
    meta = service.get_refresh_metadata()

    assert meta["last_warning_count"] == 1
    assert meta["last_warning_summary"] == (
        "BNB RSS feed could not be parsed. "
        "Other feeds were processed successfully."
    )
    assert "invalid token" not in meta["last_warning_summary"]

    stored = MetadataRepository(db_session).get(NEWS_LAST_WARNING_SUMMARY)
    assert stored == meta["last_warning_summary"]


def test_metadata_repository_upsert(db_session):
    repo = MetadataRepository(db_session)
    repo.set(NEWS_LAST_REFRESH_AT, "2024-01-01T12:00:00+00:00")
    repo.set(NEWS_LAST_INSERTED_COUNT, "3")
    db_session.commit()

    repo.set(NEWS_LAST_INSERTED_COUNT, "7")
    db_session.commit()

    assert repo.get(NEWS_LAST_INSERTED_COUNT) == "7"
    assert repo.get("news_last_skipped_duplicates") is None


def test_scheduler_run_refresh_persists_metadata(db_session):
    """Scheduler uses the same NewsApplicationService.refresh path."""
    items = NewsCollector().parse_feed_content(SAMPLE_RSS, "Sched")
    mock_collector = MagicMock()
    mock_collector.fetch_feed.return_value = items

    @contextmanager
    def fake_scope():
        yield db_session

    with patch("app.tasks.news.scheduler.session_scope", fake_scope):
        with patch("app.services.news_service.NewsCollector", return_value=mock_collector):
            NewsRefreshScheduler().run_scheduled_refresh()

    service = NewsApplicationService(db_session, collector=mock_collector)
    meta = service.get_refresh_metadata()
    assert meta["last_refresh_at"] is not None
    assert meta["last_inserted_count"] == 1
