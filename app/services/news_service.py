"""Application service for financial news (Task 5)."""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logging_config import get_logger
from app.models.news import NewsArticle
from app.repositories.metadata_repository import MetadataRepository
from app.repositories.news_repository import NewsRepository
from app.tasks.news.collector import NewsCollector
from app.tasks.news.constants import DEFAULT_NEWS_LIMIT, MAX_NEWS_LIMIT
from app.tasks.news.exceptions import NewsFeedError
from app.tasks.news.metadata_keys import (
    NEWS_LAST_INSERTED_COUNT,
    NEWS_LAST_REFRESH_AT,
    NEWS_LAST_SKIPPED_DUPLICATES,
    NEWS_LAST_WARNING_COUNT,
    NEWS_LAST_WARNING_SUMMARY,
)
from app.tasks.news.models import NewsItem, RefreshCollectionResult
from app.tasks.news.sanitize import clean_summary_html
from app.tasks.news.warnings import build_news_warning_summary

logger = get_logger(__name__)


class NewsApplicationService:
    """Orchestrates RSS collection and SQLite persistence."""

    def __init__(
        self,
        session: Session,
        collector: NewsCollector | None = None,
    ) -> None:
        self._session = session
        self._repository = NewsRepository(session)
        self._metadata = MetadataRepository(session)
        self._collector = collector or NewsCollector()
        settings = get_settings()
        self._feeds = settings.news_rss_feeds

    def list_news(self, limit: int = DEFAULT_NEWS_LIMIT) -> tuple[list[NewsArticle], int]:
        """Return latest stored articles and total count."""
        limit = max(1, min(limit, MAX_NEWS_LIMIT))
        items = self._repository.get_latest(limit)
        total = self._repository.count_all()
        return items, total

    def refresh(self) -> RefreshCollectionResult:
        """Fetch all configured feeds and persist new items only."""
        result = RefreshCollectionResult()
        logger.info("News refresh started: feeds=%d", len(self._feeds))

        for feed in self._feeds:
            source = feed.get("name") or "unknown"
            url = feed.get("url") or ""
            if not url:
                result.errors.append({"source": source, "error": "Missing feed URL"})
                logger.error("Feed configuration missing URL: source=%s", source)
                continue

            try:
                items = self._collector.fetch_feed(url, source)
            except NewsFeedError as exc:
                result.errors.append({"source": source, "error": str(exc)})
                logger.error("Feed error: source=%s error=%s", source, exc)
                continue
            except Exception as exc:
                result.errors.append({"source": source, "error": str(exc)})
                logger.exception("Unexpected feed error: source=%s", source)
                continue

            for item in items:
                if self._repository.exists_by_url(item.url):
                    result.skipped_duplicates += 1
                    continue

                entity = self._repository.add_item(item)
                if entity is None:
                    result.skipped_duplicates += 1
                    continue

                result.inserted_count += 1
                result.new_items.append(item)

        self._persist_refresh_metadata(result)

        try:
            self._session.commit()
        except Exception as exc:
            self._session.rollback()
            logger.exception("Database error during news refresh")
            result.errors.append({"source": "database", "error": str(exc)})
            raise

        logger.info(
            "News refresh finished: inserted=%d skipped_duplicates=%d errors=%d",
            result.inserted_count,
            result.skipped_duplicates,
            len(result.errors),
        )
        return result

    def get_refresh_metadata(self) -> dict[str, str | int | None]:
        """Return last refresh metadata stored in SQLite."""
        raw = self._metadata.get_many(
            [
                NEWS_LAST_REFRESH_AT,
                NEWS_LAST_INSERTED_COUNT,
                NEWS_LAST_SKIPPED_DUPLICATES,
                NEWS_LAST_WARNING_COUNT,
                NEWS_LAST_WARNING_SUMMARY,
            ]
        )
        return {
            "last_refresh_at": raw[NEWS_LAST_REFRESH_AT],
            "last_inserted_count": self._parse_int(raw[NEWS_LAST_INSERTED_COUNT]),
            "last_skipped_duplicates": self._parse_int(raw[NEWS_LAST_SKIPPED_DUPLICATES]),
            "last_warning_count": self._parse_int(raw[NEWS_LAST_WARNING_COUNT]),
            "last_warning_summary": raw[NEWS_LAST_WARNING_SUMMARY] or None,
        }

    def metadata_from_result(self, result: RefreshCollectionResult) -> dict[str, str | int | None]:
        """Build metadata fields from a refresh result (same shape as API)."""
        summary = build_news_warning_summary(
            result.errors,
            inserted_count=result.inserted_count,
            skipped_duplicates=result.skipped_duplicates,
        )
        return {
            "last_refresh_at": datetime.now(timezone.utc).isoformat(),
            "last_inserted_count": result.inserted_count,
            "last_skipped_duplicates": result.skipped_duplicates,
            "last_warning_count": len(result.errors),
            "last_warning_summary": summary,
        }

    def _persist_refresh_metadata(self, result: RefreshCollectionResult) -> None:
        fields = self.metadata_from_result(result)
        self._metadata.set(NEWS_LAST_REFRESH_AT, fields["last_refresh_at"])
        self._metadata.set(NEWS_LAST_INSERTED_COUNT, str(fields["last_inserted_count"]))
        self._metadata.set(
            NEWS_LAST_SKIPPED_DUPLICATES,
            str(fields["last_skipped_duplicates"]),
        )
        self._metadata.set(NEWS_LAST_WARNING_COUNT, str(fields["last_warning_count"]))
        self._metadata.set(
            NEWS_LAST_WARNING_SUMMARY,
            fields["last_warning_summary"] or "",
        )

    @staticmethod
    def _parse_int(value: str | None) -> int | None:
        if value is None:
            return None
        try:
            return int(value)
        except ValueError:
            return None

    @staticmethod
    def to_item_dict(article: NewsArticle) -> dict:
        return {
            "id": article.id,
            "title": article.title,
            "url": article.url,
            "summary": clean_summary_html(article.summary),
            "source": article.source,
            "published_at": article.published_at.isoformat() if article.published_at else None,
            "collected_at": article.collected_at.isoformat(),
        }

    @staticmethod
    def news_item_to_dict(item: NewsItem) -> dict:
        return {
            "title": item.title,
            "url": item.url,
            "summary": clean_summary_html(item.summary),
            "source": item.source,
            "published_at": item.published_at.isoformat() if item.published_at else None,
            "collected_at": item.collected_at.isoformat(),
        }
