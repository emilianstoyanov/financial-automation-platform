"""Fetch HTML pages: requests first, optional Playwright fallback for JS-heavy pages."""

from __future__ import annotations

import logging
import requests
from typing import TYPE_CHECKING
from urllib3.exceptions import LocationParseError
from app.tasks.scraping.exceptions import ScrapingPageError
from app.tasks.scraping.http_session import build_browser_headers, decode_response_text
from app.tasks.scraping.cloudflare import cloudflare_blocked_message, is_cloudflare_challenge
from app.tasks.scraping.constants import (
    PLAYWRIGHT_NAVIGATION_TIMEOUT_MS,
    PLAYWRIGHT_NETWORK_IDLE_TIMEOUT_MS,
    REQUEST_TIMEOUT_SECONDS,
    USER_AGENT,
)

if TYPE_CHECKING:
    from requests import Session

logger = logging.getLogger(__name__)


class PageFetcher:
    """Fetch page HTML via requests; optional Playwright when that response is unusable."""

    def __init__(
            self,
            session: Session,
            *,
            use_curl_impersonate: bool = False,
            use_browser_fallback: bool = False,
            browser_headed: bool = False,
    ) -> None:
        self._session = session
        self._use_curl = use_curl_impersonate
        self._use_browser = use_browser_fallback
        self._browser_headed = browser_headed

    def fetch(self, page_url: str, referer: str | None = None) -> str:
        """Return HTML using requests, then optional curl_cffi / Playwright fallbacks."""
        headers = build_browser_headers(referer=referer, navigation=True)
        try:
            response = self._session.get(
                page_url,
                timeout=REQUEST_TIMEOUT_SECONDS,
                headers=headers,
            )
        except requests.Timeout as exc:
            raise ScrapingPageError("Page request timed out") from exc
        except LocationParseError as exc:
            raise ScrapingPageError("Page request failed: invalid host") from exc
        except requests.RequestException as exc:
            raise ScrapingPageError(f"Page request failed: {exc}") from exc

        html = decode_response_text(response)
        error_body = html
        if response.status_code < 400 and not is_cloudflare_challenge(
                response.status_code, html, dict(response.headers)
        ):
            return html

        if self._use_curl:
            html = self._fetch_curl(page_url, referer)
            if html:
                return html

        browser_tried = False
        if self._use_browser:
            browser_tried = True
            logger.info(
                "Playwright fallback: normal HTTP fetch was not usable for %s",
                page_url,
            )
            html = self._fetch_playwright(page_url, referer=referer or None)
            if html:
                return html
        elif is_cloudflare_challenge(
                response.status_code, error_body, dict(response.headers)
        ):
            logger.warning(
                "Protected page detected but SCRAPING_BROWSER_FALLBACK is false — "
                "set it in .env and restart the server"
            )

        self._raise_for_response(
            page_url,
            response.status_code,
            error_body,
            response.headers,
            browser_fallback_enabled=self._use_browser,
            browser_fallback_tried=browser_tried,
        )

    def _raise_for_response(
            self,
            page_url: str,
            status_code: int,
            body: str,
            headers: requests.structures.CaseInsensitiveDict[str],
            *,
            browser_fallback_enabled: bool = False,
            browser_fallback_tried: bool = False,
    ) -> None:
        from urllib.parse import urlparse

        host = urlparse(page_url).netloc
        if is_cloudflare_challenge(status_code, body, dict(headers)):
            raise ScrapingPageError(
                cloudflare_blocked_message(
                    host,
                    browser_fallback_enabled=browser_fallback_enabled,
                    browser_fallback_tried=browser_fallback_tried,
                )
            )
        if status_code == 403:
            raise ScrapingPageError(
                "Access forbidden (403) — site may block automated clients"
            )
        if status_code == 404:
            raise ScrapingPageError("Page not found (404)")
        if status_code >= 400:
            raise ScrapingPageError(f"HTTP {status_code}")
        raise ScrapingPageError("Page response blocked or empty")

    def _fetch_curl(self, page_url: str, referer: str | None) -> str | None:
        try:
            from curl_cffi import requests as curl_requests
        except ImportError:
            logger.debug("curl_cffi not installed; skipping TLS impersonation")
            return None

        headers = build_browser_headers(referer=referer, navigation=True)
        try:
            response = curl_requests.get(
                page_url,
                headers=headers,
                timeout=REQUEST_TIMEOUT_SECONDS,
                impersonate="chrome124",
            )
        except Exception as exc:
            logger.warning("curl_cffi fetch failed for %s: %s", page_url, exc)
            return None

        html = decode_response_text(response)
        if response.status_code < 400 and not is_cloudflare_challenge(
                response.status_code, html, dict(response.headers)
        ):
            logger.info("Fetched %s via curl_cffi impersonation", page_url)
            return html
        return None

    def _fetch_playwright(self, page_url: str, referer: str | None = None) -> str | None:
        """Load the page in headless Chromium; return HTML or None if still blocked."""
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            logger.warning(
                "Playwright fallback skipped for %s: playwright not installed",
                page_url,
            )
            return None

        headless = not self._browser_headed
        if self._browser_headed:
            logger.warning(
                "Playwright headed mode is for local debugging only (not CAPTCHA bypass)"
            )

        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=headless)
                context = browser.new_context(
                    locale="bg-BG",
                    user_agent=USER_AGENT,
                    viewport={"width": 1920, "height": 1080},
                )
                try:
                    page = context.new_page()
                    goto_kwargs: dict = {
                        "wait_until": "domcontentloaded",
                        "timeout": PLAYWRIGHT_NAVIGATION_TIMEOUT_MS,
                    }
                    if referer:
                        goto_kwargs["referer"] = referer
                    page.goto(page_url, **goto_kwargs)

                    try:
                        page.wait_for_load_state(
                            "networkidle",
                            timeout=PLAYWRIGHT_NETWORK_IDLE_TIMEOUT_MS,
                        )
                    except Exception:
                        logger.debug(
                            "networkidle not reached for %s; using DOM after domcontentloaded",
                            page_url,
                        )

                    html = page.content()
                    if is_cloudflare_challenge(200, html, {}):
                        logger.warning(
                            "Playwright fallback could not obtain public HTML for %s "
                            "(no CAPTCHA/WAF bypass attempted)",
                            page_url,
                        )
                        return None

                    self._copy_cookies_to_session(context)
                    logger.info("Playwright fallback succeeded for %s", page_url)
                    return html
                finally:
                    context.close()
                    browser.close()
        except Exception as exc:
            logger.warning("Playwright fallback failed for %s: %s", page_url, exc)
            return None

    def _copy_cookies_to_session(self, context) -> None:
        """Share session cookies with requests for subsequent PDF downloads."""
        for cookie in context.cookies():
            domain = cookie.get("domain") or ""
            path = cookie.get("path") or "/"
            self._session.cookies.set(
                cookie["name"],
                cookie["value"],
                domain=domain.lstrip("."),
                path=path,
            )
