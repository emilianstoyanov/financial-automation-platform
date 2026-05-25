"""News constants helper tests."""

from app.tasks.news.constants import (
    DEFAULT_NEWS_RSS_FEEDS,
    news_feed_source_entries,
    news_feed_source_names,
    news_feed_source_slug,
)


def test_news_feed_source_names_defaults():
    names = news_feed_source_names()
    assert names == ["BNB", "Investor.bg", "Capital"]


def test_news_feed_source_entries_defaults():
    entries = news_feed_source_entries()
    assert entries == [
        {"name": "BNB", "slug": "bnb"},
        {"name": "Investor.bg", "slug": "investor-bg"},
        {"name": "Capital", "slug": "capital"},
    ]


def test_news_feed_source_slug():
    assert news_feed_source_slug("Investor.bg") == "investor-bg"


def test_news_feed_source_names_custom_feeds():
    feeds = [
        {"name": "Custom", "url": "http://example.com/feed"},
        {"url": "http://example.com/no-name"},
    ]
    assert news_feed_source_names(feeds) == ["Custom", "http://example.com/no-name"]


def test_news_feed_source_names_matches_default_config():
    assert news_feed_source_names(DEFAULT_NEWS_RSS_FEEDS) == [
        "BNB",
        "Investor.bg",
        "Capital",
    ]
