"""Task 3 user-friendly scrape URL error messages."""

from app.tasks.scraping.warnings import (
    SCRAPE_INVALID_OR_UNREACHABLE_URL_MESSAGE,
    friendly_scrape_url_error_message,
)


def test_friendly_message_for_invalid_url_prefix():
    raw = "Invalid URL: http://"
    assert friendly_scrape_url_error_message(raw) == SCRAPE_INVALID_OR_UNREACHABLE_URL_MESSAGE


def test_friendly_message_for_page_request_failure():
    raw = "https://example.com: Page request failed: Connection refused"
    assert friendly_scrape_url_error_message(raw) == SCRAPE_INVALID_OR_UNREACHABLE_URL_MESSAGE


def test_friendly_message_keeps_cloudflare_text():
    raw = "https://www.minfin.bg/bg/1394: Access blocked by Cloudflare on www.minfin.bg"
    assert friendly_scrape_url_error_message(raw) == raw


def test_friendly_message_for_request_failed_fallback():
    assert (
        friendly_scrape_url_error_message("Request failed")
        == SCRAPE_INVALID_OR_UNREACHABLE_URL_MESSAGE
    )
