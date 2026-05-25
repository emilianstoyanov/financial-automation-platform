"""User-friendly RSS feed warning messages (Task 5 dashboard)."""


def _is_parse_issue(raw_error: str) -> bool:
    lower = raw_error.lower()
    markers = (
        "broken feed",
        "not well-formed",
        "invalid token",
        "<unknown>",
        "bozo",
    )
    return any(marker in lower for marker in markers)


def friendly_feed_warning_message(
    source: str,
    raw_error: str,
    *,
    other_feeds_succeeded: bool,
) -> str:
    """Map a collector error to a short message without raw parser details."""
    name = (source or "").strip() or "Unknown feed"
    lower = (raw_error or "").lower()

    if _is_parse_issue(raw_error):
        if other_feeds_succeeded:
            return (
                f"{name} RSS feed could not be parsed. "
                "Other feeds were processed successfully."
            )
        return f"{name} RSS feed could not be parsed."

    if "missing feed url" in lower:
        return f"{name} feed is not configured correctly."

    if other_feeds_succeeded:
        return (
            f"{name} feed could not be loaded. "
            "Other feeds were processed successfully."
        )
    return f"{name} feed could not be loaded."


def build_news_warning_summary(
    errors: list[dict[str, str]],
    *,
    inserted_count: int,
    skipped_duplicates: int,
) -> str | None:
    """Build a single-line summary for the Last Updated panel."""
    feed_errors = [e for e in errors if e.get("source") not in (None, "", "database")]
    if not feed_errors:
        return None

    other_succeeded = (inserted_count + skipped_duplicates) > 0

    if len(feed_errors) > 1:
        if other_succeeded:
            return (
                "Some RSS feeds could not be parsed. "
                "Other feeds were processed successfully."
            )
        return "Some RSS feeds could not be loaded."

    return friendly_feed_warning_message(
        str(feed_errors[0].get("source", "")),
        str(feed_errors[0].get("error", "")),
        other_feeds_succeeded=other_succeeded,
    )
