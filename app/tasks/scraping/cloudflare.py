"""Cloudflare / bot-protection detection for scraping responses."""

from __future__ import annotations

_CF_BODY_MARKERS = (
    "just a moment",
    "cf-browser-verification",
    "challenges.cloudflare.com",
    "cdn-cgi/challenge-platform",
    "attention required! | cloudflare",
)
_CF_HEADER_MARKERS = ("cf-mitigated", "cf-ray")


def is_cloudflare_challenge(
    status_code: int,
    body: str,
    headers: dict[str, str] | None = None,
) -> bool:
    """Return True when the response looks like a Cloudflare bot challenge."""
    lowered = body.lower()
    if any(marker in lowered for marker in _CF_BODY_MARKERS):
        return True
    if headers:
        header_blob = " ".join(f"{key}:{value}" for key, value in headers.items()).lower()
        if any(marker in header_blob for marker in _CF_HEADER_MARKERS):
            if status_code in {403, 503} or "challenge" in lowered:
                return True
    return status_code == 403 and len(body) < 20_000 and "cloudflare" in lowered


def cloudflare_blocked_message(
    host: str,
    *,
    browser_fallback_enabled: bool = False,
    browser_fallback_tried: bool = False,
) -> str:
    """Human-readable guidance when Cloudflare blocks automated access."""
    base = (
        f"Access blocked by Cloudflare on {host} — bot protection, "
        "not a login/CAPTCHA we can ethically bypass. "
    )
    if not browser_fallback_enabled:
        return (
            base
            + "Playwright was NOT used: set SCRAPING_BROWSER_FALLBACK=true in .env "
            "(copy from .env.example) and restart the server."
        )
    if browser_fallback_tried:
        return (
            base
            + "Playwright was tried but Cloudflare still blocked (common on some networks). "
            "Use scrape-html with HTML saved from your browser, or direct PDF URLs."
        )
    return (
        base
        + "Use scrape-html with HTML saved from your browser, offline:… in sample_urls.txt, "
        "or direct PDF URLs."
    )
