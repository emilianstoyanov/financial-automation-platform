"""Document scraper for financial portal PDF extraction."""

import json
import time
import random
import requests
from pathlib import Path
from urllib.parse import urlparse
from datetime import datetime, timezone
from app.core.config import get_settings
from app.core.data_dirs import ensure_data_directories
from app.tasks.scraping.constants import (
    DEFAULT_OUTPUT_JSON,
    DEFAULT_SCRAPING_LOG,
    DEFAULT_URLS_FILE,
    DOCUMENT_TYPE_PDF,
    MAX_DELAY_SECONDS,
    MAX_PDFS_PER_PAGE,
    MIN_DELAY_SECONDS,
    PREVIEW_MAX_CHARS,
    REQUEST_TIMEOUT_SECONDS,
)
from app.tasks.scraping.exceptions import (
    ScrapingInvalidURLError,
    ScrapingPageError,
    ScrapingPDFError,
)
from app.tasks.scraping.http_session import (
    build_browser_headers,
    build_session,
    site_root_url,
)
from app.tasks.scraping.logging_setup import setup_scraping_logging
from app.tasks.scraping.models import ScrapedDocument, ScrapingResult
from app.tasks.scraping.page_fetcher import PageFetcher
from app.tasks.scraping.parsers import (
    PdfLinkCandidate,
    ScrapeTarget,
    find_document_portal_links,
    find_pdf_links,
    is_pdf_url,
    parse_scrape_line,
    read_scrape_targets_from_file,
    truncate_preview,
    validate_url,
)
from app.tasks.scraping.pdf_extractor import download_pdf, extract_pdf_text

logger = setup_scraping_logging()


class DocumentScraper:
    """Orchestrate page fetch, PDF discovery, download, text extraction, and JSON output.

    Supports live URLs, offline HTML (``offline:path|page_url``), and optional Playwright
    fallback for bot-protected sites. Failed pages are recorded without stopping the run.
    """

    def __init__(
            self,
            urls_file: str | Path = DEFAULT_URLS_FILE,
            output_json: str | Path = DEFAULT_OUTPUT_JSON,
            log_file: str = DEFAULT_SCRAPING_LOG,
    ) -> None:
        """Configure input URL list, JSON output path, and log file."""
        self.urls_file = Path(urls_file)
        self.output_json = Path(output_json)
        self.log_file = log_file
        self._session = build_session()
        self._warmed_hosts: set[str] = set()
        settings = get_settings()
        self._page_fetcher = PageFetcher(
            self._session,
            use_curl_impersonate=settings.scraping_use_curl_impersonate,
            use_browser_fallback=settings.scraping_browser_fallback,
            browser_headed=settings.scraping_playwright_headed,
        )

    def process_local_urls(self, persist: bool = True) -> ScrapingResult:
        """Read URLs from ``sample_urls.txt`` and scrape each page."""
        targets = read_scrape_targets_from_file(self.urls_file)
        return self.process_targets(targets, persist=persist)

    def scrape_url(self, url: str, persist: bool = True) -> ScrapingResult:
        """Scrape a single page URL for PDF documents."""
        return self.process_targets([parse_scrape_line(url)], persist=persist)

    def scrape_html(self, html: str, page_url: str, persist: bool = True) -> ScrapingResult:
        """Scrape PDF links from HTML saved in a browser (bypasses live Cloudflare fetch)."""
        validate_url(page_url)
        target = ScrapeTarget(page_url=page_url, html=html)
        return self.process_targets([target], persist=persist)

    def process_urls(self, urls: list[str], persist: bool = True) -> ScrapingResult:
        """Scrape each URL string with delays and optionally save aggregated JSON."""
        targets = [parse_scrape_line(url) for url in urls]
        return self.process_targets(targets, persist=persist)

    def process_targets(
            self, targets: list[ScrapeTarget], persist: bool = True
    ) -> ScrapingResult:
        """Scrape each target with delays and optionally save aggregated JSON."""
        ensure_data_directories()
        setup_scraping_logging(self.log_file)

        documents: list[ScrapedDocument] = []
        errors: list[str] = []

        logger.info("Scraping started: %s target(s)", len(targets))
        for index, target in enumerate(targets):
            if index > 0:
                self._delay_between_requests()

            try:
                page_docs = self._scrape_target(target)
                documents.extend(page_docs)
                logger.info(
                    "Page complete: %s — %s document(s) saved",
                    target.page_url,
                    len(page_docs),
                )
            except ScrapingInvalidURLError as exc:
                message = str(exc)
                errors.append(message)
                logger.warning("Invalid URL skipped: %s", message)
            except ScrapingPageError as exc:
                message = f"{target.page_url}: {exc}"
                errors.append(message)
                logger.warning("Page blocked or failed: %s", message)

        status = "success" if documents else "partial" if errors else "success"
        if not documents and errors:
            status = "failed"

        result = ScrapingResult(status=status, documents=documents, errors=errors)
        if persist:
            self._save_results(result)

        logger.info(
            "Scraping finished: %s document(s), %s error(s), status=%s",
            len(documents),
            len(errors),
            status,
        )
        return result

    def _scrape_target(self, target: ScrapeTarget) -> list[ScrapedDocument]:
        """Fetch or load HTML and process up to MAX_PDFS_PER_PAGE PDF links."""
        page_url = target.page_url
        if is_pdf_url(page_url):
            candidate = PdfLinkCandidate(
                url=page_url,
                title=Path(urlparse(page_url).path).name or page_url,
                date_published=None,
            )
            return [self._process_pdf(candidate, page_url)]

        html = target.html if target.html is not None else self._fetch_page_html(page_url)
        return self._scrape_html(html, page_url)

    def _scrape_html(self, html: str, page_url: str) -> list[ScrapedDocument]:
        """Extract PDF links from HTML and download each file."""
        candidates = find_pdf_links(html, page_url)
        if len(candidates) < MAX_PDFS_PER_PAGE:
            candidates = self._append_pdfs_from_document_portals(
                html, page_url, candidates
            )

        if not candidates:
            logger.info("No PDF links found on %s", page_url)
            return []

        logger.info(
            "Found %s PDF link(s) on %s",
            len(candidates),
            page_url,
        )
        for candidate in candidates:
            logger.info("PDF link: %s", candidate.url)

        documents: list[ScrapedDocument] = []
        for candidate in candidates:
            try:
                documents.append(self._process_pdf(candidate, page_url))
            except ScrapingPDFError as exc:
                logger.warning("PDF extraction failed for %s: %s", candidate.url, exc)
        return documents

    def _append_pdfs_from_document_portals(
            self,
            html: str,
            page_url: str,
            candidates: list[PdfLinkCandidate],
    ) -> list[PdfLinkCandidate]:
        """Follow catalog pages (e.g. NSI /documents/215) and collect nested .pdf links."""
        seen = {item.url for item in candidates}
        merged = list(candidates)

        for portal in find_document_portal_links(html, page_url):
            if len(merged) >= MAX_PDFS_PER_PAGE:
                break
            try:
                portal_html = self._fetch_page_html(portal.url)
            except ScrapingPageError as exc:
                logger.debug("Skipping portal %s: %s", portal.url, exc)
                continue

            for nested in find_pdf_links(portal_html, portal.url):
                if nested.url in seen:
                    continue
                seen.add(nested.url)
                merged.append(nested)
                if len(merged) >= MAX_PDFS_PER_PAGE:
                    break

        return merged

    def _fetch_page_html(self, page_url: str) -> str:
        """Download HTML for a page URL using browser-like headers and fallbacks."""
        validate_url(page_url)
        root_url = site_root_url(page_url)
        self._warm_up_host(root_url)
        return self._page_fetcher.fetch(page_url, referer=root_url)

    def _warm_up_host(self, root_url: str) -> None:
        """Request site root once per host to establish cookies before deep pages."""
        host = urlparse(root_url).netloc
        if host in self._warmed_hosts:
            return

        try:
            self._session.get(
                root_url,
                timeout=REQUEST_TIMEOUT_SECONDS,
                headers=build_browser_headers(referer=root_url, navigation=True),
            )
            logger.debug("Warmed up session for %s", host)
        except requests.RequestException as exc:
            logger.debug("Host warm-up failed for %s: %s", root_url, exc)

        self._warmed_hosts.add(host)

    def _process_pdf(self, candidate: PdfLinkCandidate, source_page: str) -> ScrapedDocument:
        """Download a PDF, extract text, and build metadata plus a 500-char preview."""
        pdf_bytes, size_kb = download_pdf(
            candidate.url,
            self._session,
            referer=source_page,
        )
        logger.info("Downloaded PDF (%s KB): %s", size_kb, candidate.url)
        text = extract_pdf_text(pdf_bytes)
        preview = truncate_preview(text, PREVIEW_MAX_CHARS)

        return ScrapedDocument(
            title=candidate.title,
            url=candidate.url,
            size_kb=size_kb,
            date_published=candidate.date_published,
            document_type=DOCUMENT_TYPE_PDF,
            content_preview=preview,
            scraped_at=datetime.now(timezone.utc).isoformat(),
            source_page=source_page,
        )

    def _delay_between_requests(self) -> None:
        """Sleep a random interval between 1 and 2 seconds."""
        delay = random.uniform(MIN_DELAY_SECONDS, MAX_DELAY_SECONDS)
        time.sleep(delay)

    def _save_results(self, result: ScrapingResult) -> None:
        """Write scraped documents to ``extracted_documents.json``."""
        self.output_json.parent.mkdir(parents=True, exist_ok=True)
        with self.output_json.open("w", encoding="utf-8") as handle:
            json.dump(result.to_json_payload(), handle, indent=2, ensure_ascii=False)
        logger.info("Saved scraping results to %s", self.output_json)
