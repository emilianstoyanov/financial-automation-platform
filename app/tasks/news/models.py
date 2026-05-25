"""Domain models for RSS news collection."""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class NewsItem:
    """Parsed news article from an RSS feed."""

    title: str
    url: str
    summary: str
    source: str
    published_at: datetime | None
    collected_at: datetime


@dataclass
class RefreshFeedResult:
    """Result of processing a single RSS feed."""

    source: str
    fetched_count: int = 0
    error: str | None = None


@dataclass
class RefreshCollectionResult:
    """Aggregated result of refreshing all configured feeds."""

    inserted_count: int = 0
    skipped_duplicates: int = 0
    errors: list[dict[str, str]] = field(default_factory=list)
    feed_results: list[RefreshFeedResult] = field(default_factory=list)
    new_items: list[NewsItem] = field(default_factory=list)
