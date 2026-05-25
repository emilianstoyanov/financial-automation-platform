"""RSS financial news collection (Task 5)."""

from app.tasks.news.models import NewsItem, RefreshCollectionResult, RefreshFeedResult

__all__ = [
    "NewsCollector",
    "NewsItem",
    "NewsRefreshScheduler",
    "RefreshCollectionResult",
    "RefreshFeedResult",
]


def __getattr__(name: str):
    if name == "NewsCollector":
        from app.tasks.news.collector import NewsCollector

        return NewsCollector
    if name == "NewsRefreshScheduler":
        from app.tasks.news.scheduler import NewsRefreshScheduler

        return NewsRefreshScheduler
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
