"""Tests for PageFetcher: requests default path and Playwright fallback."""

from unittest.mock import MagicMock, patch

import pytest

from app.tasks.scraping.exceptions import ScrapingPageError
from app.tasks.scraping.http_session import build_session
from app.tasks.scraping.page_fetcher import PageFetcher


def test_fetch_returns_requests_html_without_playwright():
    """Successful requests response is used; Playwright is not invoked."""
    session = build_session()
    fetcher = PageFetcher(session, use_browser_fallback=True)
    html_body = "<html><a href='/doc.pdf'>PDF</a></html>"
    response = MagicMock()
    response.status_code = 200
    response.text = html_body
    response.content = html_body.encode("utf-8")
    response.encoding = "utf-8"
    response.headers = {}

    with patch.object(session, "get", return_value=response) as mock_get, patch.object(
        fetcher, "_fetch_playwright"
    ) as mock_pw:
        html = fetcher.fetch("https://example.com/page")

    assert "doc.pdf" in html
    mock_get.assert_called_once()
    mock_pw.assert_not_called()


def test_fetch_uses_playwright_only_after_failed_http():
    """Playwright runs only when the HTTP response is blocked or unusable."""
    session = build_session()
    fetcher = PageFetcher(session, use_browser_fallback=True)
    blocked_html = "<title>Just a moment...</title>"
    response = MagicMock()
    response.status_code = 403
    response.text = blocked_html
    response.content = blocked_html.encode("utf-8")
    response.encoding = "utf-8"
    response.headers = {}

    with patch.object(session, "get", return_value=response), patch.object(
        fetcher,
        "_fetch_playwright",
        return_value="<html><a href='/ok.pdf'>OK</a></html>",
    ) as mock_pw:
        html = fetcher.fetch("https://blocked.example/page")

    assert "ok.pdf" in html
    mock_pw.assert_called_once()


def test_fetch_raises_when_playwright_still_blocked():
    """No CAPTCHA bypass: failure is reported when Playwright HTML is still blocked."""
    session = build_session()
    fetcher = PageFetcher(session, use_browser_fallback=True)
    blocked_html = "<title>Just a moment...</title>"
    response = MagicMock()
    response.status_code = 403
    response.text = blocked_html
    response.content = blocked_html.encode("utf-8")
    response.encoding = "utf-8"
    response.headers = {}

    with patch.object(session, "get", return_value=response), patch.object(
        fetcher, "_fetch_playwright", return_value=None
    ), pytest.raises(ScrapingPageError, match="Playwright was tried"):
        fetcher.fetch("https://www.minfin.bg/bg/1394")
