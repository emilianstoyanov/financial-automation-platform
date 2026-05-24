"""Service layer for document scraping operations."""

from pathlib import Path
from app.tasks.scraping.models import ScrapingResult
from app.tasks.scraping.scraper import DocumentScraper
from app.tasks.scraping.exceptions import ScrapingInvalidURLError
from app.tasks.scraping.constants import DEFAULT_OUTPUT_JSON, DEFAULT_URLS_FILE


class ScrapingApplicationService:
    """Application service wrapping ``DocumentScraper`` for API routes."""

    def __init__(
            self,
            urls_file: str | Path = DEFAULT_URLS_FILE,
            output_json: str | Path = DEFAULT_OUTPUT_JSON,
    ) -> None:
        self._scraper = DocumentScraper(
            urls_file=urls_file,
            output_json=output_json,
        )

    def process_local_urls(self, persist: bool = True) -> ScrapingResult:
        """Scrape all URLs listed in ``data/scraping/sample_urls.txt``."""
        if not self._scraper.urls_file.is_file():
            raise ScrapingInvalidURLError(
                f"URL file not found: {self._scraper.urls_file}"
            )
        return self._scraper.process_local_urls(persist=persist)

    def scrape_url(self, url: str, persist: bool = True) -> ScrapingResult:
        """Scrape PDF documents from a single page URL."""
        return self._scraper.scrape_url(url, persist=persist)

    def scrape_html(
            self, html: str, page_url: str, persist: bool = True
    ) -> ScrapingResult:
        """Scrape PDF links from browser-saved HTML (for Cloudflare-protected pages)."""
        return self._scraper.scrape_html(html, page_url, persist=persist)
