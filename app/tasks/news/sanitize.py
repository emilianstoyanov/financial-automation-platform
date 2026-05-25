"""Plain-text cleanup for RSS summary HTML."""

from __future__ import annotations

import html
import re

_TAG_RE = re.compile(r"<[^>]+>", re.IGNORECASE)
_WHITESPACE_RE = re.compile(r"\s+")


def clean_summary_html(summary: str | None) -> str:
    """Strip HTML, decode entities, and normalize whitespace for display."""
    if not summary:
        return ""

    text = html.unescape(summary)
    text = _TAG_RE.sub(" ", text)
    text = _WHITESPACE_RE.sub(" ", text).strip()
    return text
