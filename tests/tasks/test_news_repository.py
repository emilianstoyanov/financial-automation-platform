"""Tests for news repository and duplicate handling."""

from datetime import datetime, timezone

from app.repositories.news_repository import NewsRepository
from app.tasks.news.models import NewsItem

SAMPLE_ITEM = NewsItem(
    title="Test headline",
    url="https://example.com/article-1",
    summary="Short summary",
    source="TestFeed",
    published_at=datetime(2024, 1, 15, 10, 0, tzinfo=timezone.utc),
    collected_at=datetime(2024, 1, 16, 12, 0, tzinfo=timezone.utc),
)


def test_save_and_read_news(db_session):
    repo = NewsRepository(db_session)
    entity = repo.add_item(SAMPLE_ITEM)
    assert entity is not None
    assert entity.id is not None
    db_session.commit()

    latest = repo.get_latest(limit=5)
    assert len(latest) == 1
    assert latest[0].url == SAMPLE_ITEM.url
    assert repo.count_all() == 1


def test_duplicate_url_not_inserted_twice(db_session):
    repo = NewsRepository(db_session)
    first = repo.add_item(SAMPLE_ITEM)
    second = repo.add_item(SAMPLE_ITEM)
    db_session.commit()

    assert first is not None
    assert second is None
    assert repo.exists_by_url(SAMPLE_ITEM.url)
    assert repo.count_all() == 1
