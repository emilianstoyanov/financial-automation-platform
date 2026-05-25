"""Default RSS feed configuration for financial news."""

import re

DEFAULT_NEWS_RSS_FEEDS: list[dict[str, str]] = [
    {
        "name": "BNB",
        "url": "https://www.bnb.bg/PressOffice/PONeWS/rss/en/rss.xml",
    },
    {
        "name": "Investor.bg",
        "url": "https://www.investor.bg/rss/news",
    },
    {
        "name": "Capital",
        "url": "https://www.capital.bg/rss/",
    },
]

DEFAULT_NEWS_LIMIT = 10
MAX_NEWS_LIMIT = 100


def _feed_display_name(feed: dict[str, str]) -> str | None:
    name = (feed.get("name") or "").strip()
    if name:
        return name
    url = (feed.get("url") or "").strip()
    return url or None


def news_feed_source_slug(name: str) -> str:
    """CSS-safe slug from a feed display name."""
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "feed"


def news_feed_source_names(feeds: list[dict[str, str]] | None = None) -> list[str]:
    """Return display names for configured RSS feeds (name, else url)."""
    return [entry["name"] for entry in news_feed_source_entries(feeds)]


def news_feed_source_entries(
    feeds: list[dict[str, str]] | None = None,
) -> list[dict[str, str]]:
    """Return {name, slug} entries for dashboard source badges."""
    feed_list = feeds if feeds is not None else DEFAULT_NEWS_RSS_FEEDS
    entries: list[dict[str, str]] = []
    for feed in feed_list:
        display = _feed_display_name(feed)
        if display:
            entries.append({"name": display, "slug": news_feed_source_slug(display)})
    return entries
