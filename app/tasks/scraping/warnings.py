"""User-friendly scrape URL error messages (Task 3 dashboard)."""

from typing import Final

SCRAPE_INVALID_OR_UNREACHABLE_URL_MESSAGE: Final[str] = (
    "Invalid or unreachable URL. Please check the address and try again."
)

_BLOCKED_MARKERS = (
    "cloudflare",
    "blocked",
    "forbidden",
    "403",
    "captcha",
    "waf",
)

_UNREACHABLE_MARKERS = (
    "invalid url:",
    "page request failed",
    "page request timed out",
    "page not found",
    "page response blocked or empty",
    "failed to parse",
    "label empty or too long",
    "name or service not known",
    "getaddrinfo",
    "nodename nor servname",
    "no route to host",
    "connection refused",
    "max retries exceeded",
    "newconnectionerror",
    "locationparseerror",
    "unprocessable entity",
    "request failed",
)


def is_scrape_blocked_error(message: str) -> bool:
    """True when the error is Cloudflare or similar bot protection."""
    lower = (message or "").lower()
    return any(marker in lower for marker in _BLOCKED_MARKERS)


def is_scrape_url_unreachable_error(message: str) -> bool:
    """True when the error looks like a bad or unreachable page URL."""
    if is_scrape_blocked_error(message):
        return False
    lower = (message or "").lower()
    return any(marker in lower for marker in _UNREACHABLE_MARKERS)


def friendly_scrape_url_error_message(raw_error: str) -> str:
    """Map technical scrape errors to a short message; keep blocked-site text."""
    if not raw_error or is_scrape_blocked_error(raw_error):
        return raw_error
    if is_scrape_url_unreachable_error(raw_error):
        return SCRAPE_INVALID_OR_UNREACHABLE_URL_MESSAGE
    return raw_error
