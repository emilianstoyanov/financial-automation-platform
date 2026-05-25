"""Tests for RSS summary HTML sanitization."""

from app.tasks.news.collector import NewsCollector
from app.tasks.news.sanitize import clean_summary_html


def test_removes_img_tag():
    raw = '<img src="https://example.com/a.jpg" alt="chart" /> Breaking news'
    assert clean_summary_html(raw) == "Breaking news"


def test_removes_br_tags():
    raw = "Line one<br/><br />Line two"
    assert clean_summary_html(raw) == "Line one Line two"


def test_decodes_html_entities():
    raw = "Rate &gt; 5% &amp; stable &quot;now&quot;"
    assert clean_summary_html(raw) == 'Rate > 5% & stable "now"'


def test_preserves_plain_text():
    raw = "Plain financial headline summary."
    assert clean_summary_html(raw) == raw


def test_empty_and_none_summary():
    assert clean_summary_html(None) == ""
    assert clean_summary_html("") == ""
    assert clean_summary_html("   <br/>  ") == ""


def test_collector_sanitizes_summary_from_rss():
    rss = """<?xml version="1.0"?><rss><channel>
    <item>
      <title>Headline</title>
      <link>https://example.com/1</link>
      <description>&lt;p&gt;Text &amp; more&lt;/p&gt;&lt;img src=x /&gt;</description>
    </item>
    </channel></rss>"""
    items = NewsCollector().parse_feed_content(rss, "Test")
    assert len(items) == 1
    assert "<" not in items[0].summary
    assert "Text & more" in items[0].summary
