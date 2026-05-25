"""Repository for news articles."""

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.news import NewsArticle
from app.repositories.base import BaseRepository
from app.tasks.news.models import NewsItem


class NewsRepository(BaseRepository[NewsArticle]):
    """Persistence layer for RSS news items."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, NewsArticle)

    def exists_by_url(self, url: str) -> bool:
        stmt = select(NewsArticle.id).where(NewsArticle.url == url).limit(1)
        return self._session.execute(stmt).scalar_one_or_none() is not None

    def add_item(self, item: NewsItem) -> NewsArticle | None:
        """Insert a news item; return None if URL already exists."""
        if self.exists_by_url(item.url):
            return None

        entity = NewsArticle(
            title=item.title,
            url=item.url,
            summary=item.summary,
            source=item.source,
            published_at=item.published_at,
            collected_at=item.collected_at,
        )
        try:
            return self.add(entity)
        except IntegrityError:
            self._session.rollback()
            return None

    def get_latest(self, limit: int = 10) -> list[NewsArticle]:
        stmt = (
            select(NewsArticle)
            .order_by(
                NewsArticle.published_at.desc().nulls_last(),
                NewsArticle.collected_at.desc(),
            )
            .limit(limit)
        )
        return list(self._session.scalars(stmt).all())

    def count_all(self) -> int:
        return int(self._session.scalar(select(func.count()).select_from(NewsArticle)) or 0)
