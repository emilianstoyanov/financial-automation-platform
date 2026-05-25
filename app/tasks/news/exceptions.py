"""News collection exceptions."""


class NewsError(Exception):
    """Base exception for news collection."""


class NewsFeedError(NewsError):
    """Raised when an RSS feed cannot be fetched or parsed."""


class NewsEntryError(NewsError):
    """Raised when a feed entry is missing required fields."""
