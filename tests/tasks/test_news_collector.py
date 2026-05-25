"""Unit tests for RSS news collector."""

from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from app.tasks.news.collector import NewsCollector
from app.tasks.news.exceptions import NewsEntryError, NewsFeedError

SAMPLE_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
  <title>Test Financial News</title>
  <item>
    <title>BNB raises key rate</title>
    <link>https://example.com/news/1</link>
    <description>Central bank announcement.</description>
    <pubDate>Mon, 15 Jan 2024 10:00:00 GMT</pubDate>
  </item>
  <item>
    <title>Markets rally on earnings</title>
    <link>https://example.com/news/2</link>
    <description>Investor sentiment improves.</description>
    <pubDate>Tue, 16 Jan 2024 08:30:00 GMT</pubDate>
  </item>
</channel>
</rss>"""

BROKEN_RSS = "<not-valid-rss"


def test_parse_feed_content_extracts_items():
    collector = NewsCollector()
    items = collector.parse_feed_content(SAMPLE_RSS, "TestSource")

    assert len(items) == 2
    assert items[0].title == "BNB raises key rate"
    assert items[0].url == "https://example.com/news/1"
    assert items[0].source == "TestSource"
    assert "Central bank" in items[0].summary
    assert items[0].published_at is not None
    assert items[0].collected_at.tzinfo is not None


def test_parse_feed_skips_entry_without_title():
    rss = """<?xml version="1.0"?><rss><channel>
    <item><link>https://example.com/no-title</link></item>
    <item><title>Has title</title><link>https://example.com/ok</link></item>
    </channel></rss>"""
    collector = NewsCollector()
    items = collector.parse_feed_content(rss, "Test")

    assert len(items) == 1
    assert items[0].url == "https://example.com/ok"


def test_parse_broken_feed_raises():
    collector = NewsCollector()
    with pytest.raises(NewsFeedError):
        collector.parse_feed_content(BROKEN_RSS, "Broken")


def test_parse_empty_feed_returns_empty_list():
    rss = """<?xml version="1.0"?><rss><channel><title>Empty</title></channel></rss>"""
    collector = NewsCollector()
    items = collector.parse_feed_content(rss, "Empty")
    assert items == []


def test_entry_without_link_raises_news_entry_error():
    collector = NewsCollector()
    entry = {"title": "Only title"}
    with pytest.raises(NewsEntryError):
        collector._entry_to_item(entry, "Src", datetime.now(timezone.utc))


def test_fetch_feed_network_error():
    collector = NewsCollector()
    with patch("app.tasks.news.collector.feedparser.parse", side_effect=OSError("network down")):
        with pytest.raises(NewsFeedError, match="Failed to fetch"):
            collector.fetch_feed("http://example.com/feed.xml", "Net")
