"""RSS feed collector using feedparser."""

from __future__ import annotations

import calendar
from datetime import datetime, timezone

import feedparser

from app.core.logging_config import get_logger
from app.tasks.news.exceptions import NewsEntryError, NewsFeedError
from app.tasks.news.models import NewsItem
from app.tasks.news.sanitize import clean_summary_html

logger = get_logger(__name__)


class NewsCollector:
    """Fetch and parse financial news from RSS feeds."""

    def fetch_feed(self, feed_url: str, source: str) -> list[NewsItem]:
        """Parse an RSS feed URL and return validated news items."""
        try:
            parsed = feedparser.parse(feed_url)
        except Exception as exc:
            raise NewsFeedError(f"Failed to fetch feed {source}: {exc}") from exc

        return self._entries_from_parsed(parsed, source, feed_label=feed_url)

    def parse_feed_content(self, content: str, source: str) -> list[NewsItem]:
        """Parse RSS XML/string content (used in tests)."""
        try:
            parsed = feedparser.parse(content)
        except Exception as exc:
            raise NewsFeedError(f"Failed to parse feed {source}: {exc}") from exc

        return self._entries_from_parsed(parsed, source, feed_label=source)

    def _entries_from_parsed(
        self,
        parsed: feedparser.FeedParserDict,
        source: str,
        *,
        feed_label: str,
    ) -> list[NewsItem]:
        if getattr(parsed, "bozo", False) and not parsed.entries:
            bozo_exc = getattr(parsed, "bozo_exception", None)
            detail = str(bozo_exc) if bozo_exc else "invalid or empty feed"
            raise NewsFeedError(f"Broken feed for {source} ({feed_label}): {detail}")

        if not parsed.entries:
            logger.warning("RSS feed returned no entries: source=%s url=%s", source, feed_label)
            return []

        collected_at = datetime.now(timezone.utc)
        items: list[NewsItem] = []

        for entry in parsed.entries:
            try:
                items.append(self._entry_to_item(entry, source, collected_at))
            except NewsEntryError as exc:
                logger.warning(
                    "Skipping invalid entry: source=%s error=%s",
                    source,
                    exc,
                )

        logger.info(
            "Feed processed: source=%s entries=%d valid=%d",
            source,
            len(parsed.entries),
            len(items),
        )
        return items

    def _entry_to_item(
        self,
        entry: feedparser.FeedParserDict,
        source: str,
        collected_at: datetime,
    ) -> NewsItem:
        title = (entry.get("title") or "").strip()
        url = (entry.get("link") or entry.get("id") or "").strip()

        if not title or not url:
            raise NewsEntryError("Entry missing title or link")

        summary = clean_summary_html(entry.get("summary") or entry.get("description") or "")
        if len(summary) > 2000:
            summary = summary[:2000] + "…"

        published_at = self._parse_published(entry)

        return NewsItem(
            title=title,
            url=url,
            summary=summary,
            source=source,
            published_at=published_at,
            collected_at=collected_at,
        )

    @staticmethod
    def _parse_published(entry: feedparser.FeedParserDict) -> datetime | None:
        for key in ("published_parsed", "updated_parsed"):
            parsed_time = entry.get(key)
            if parsed_time:
                timestamp = calendar.timegm(parsed_time)
                return datetime.fromtimestamp(timestamp, tz=timezone.utc)
        return None
