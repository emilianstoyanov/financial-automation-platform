"""Tests for friendly RSS warning summaries."""

from app.tasks.news.warnings import (
    build_news_warning_summary,
    friendly_feed_warning_message,
)


def test_single_parse_warning_with_other_feeds_ok():
    msg = friendly_feed_warning_message(
        "BNB",
        "not well-formed (invalid token): line 1, column 0",
        other_feeds_succeeded=True,
    )
    assert msg == (
        "BNB RSS feed could not be parsed. "
        "Other feeds were processed successfully."
    )
    assert "invalid token" not in msg


def test_multiple_feed_errors_combined_summary():
    errors = [
        {"source": "BNB", "error": "broken feed"},
        {"source": "Other", "error": "timeout"},
    ]
    summary = build_news_warning_summary(
        errors,
        inserted_count=0,
        skipped_duplicates=5,
    )
    assert summary == (
        "Some RSS feeds could not be parsed. "
        "Other feeds were processed successfully."
    )


def test_single_feed_summary_from_errors_list():
    summary = build_news_warning_summary(
        [{"source": "BNB", "error": "<unknown>:2:5: not well-formed"}],
        inserted_count=0,
        skipped_duplicates=0,
    )
    assert summary == "BNB RSS feed could not be parsed."


def test_no_summary_when_no_errors():
    assert (
        build_news_warning_summary([], inserted_count=1, skipped_duplicates=0)
        is None
    )
