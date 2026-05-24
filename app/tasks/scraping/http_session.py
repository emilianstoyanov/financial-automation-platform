"""HTTP session setup with browser-like headers for public scraping."""

import requests
from urllib.parse import urlparse
from app.tasks.scraping.constants import USER_AGENT

DEFAULT_ACCEPT = (
    "text/html,application/xhtml+xml,application/xml;q=0.9,"
    "image/avif,image/webp,image/apng,*/*;q=0.8"
)
PDF_ACCEPT = "application/pdf,application/octet-stream,*/*;q=0.8"


def site_root_url(url: str) -> str:
    """Return scheme + host root URL for use as Referer."""
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}/"


def build_browser_headers(
        referer: str | None = None,
        *,
        accept: str = DEFAULT_ACCEPT,
        navigation: bool = True,
) -> dict[str, str]:
    """Build headers that resemble a normal desktop browser request."""
    headers: dict[str, str] = {
        "User-Agent": USER_AGENT,
        "Accept": accept,
        "Accept-Language": "bg-BG,bg;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }
    if referer:
        headers["Referer"] = referer
    if navigation:
        headers.update(
            {
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "same-origin" if referer else "none",
                "Sec-Fetch-User": "?1",
            }
        )
    return headers


def build_session() -> requests.Session:
    """Create a session with default browser-like headers."""
    session = requests.Session()
    session.headers.update(build_browser_headers(navigation=False))
    return session
