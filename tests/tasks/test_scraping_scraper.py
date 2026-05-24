"""Unit tests for DocumentScraper."""

import pytest
from unittest.mock import MagicMock, patch
from app.tasks.scraping.parsers import ScrapeTarget
from app.tasks.scraping.scraper import DocumentScraper
from app.tasks.scraping.exceptions import ScrapingPDFError
from app.tasks.scraping.pdf_extractor import extract_pdf_text

SAMPLE_HTML = """
<html><body>
  <a href="https://example.com/files/report.pdf">Report 2024</a>
  <a href="https://example.com/files/other.pdf">Other</a>
  <a href="https://example.com/files/third.pdf">Third</a>
</body></html>
"""


def test_scrape_page_downloads_and_extracts_pdfs(tmp_path):
    """Scraper downloads PDFs and builds document records with previews."""
    scraper = DocumentScraper(
        urls_file=tmp_path / "urls.txt",
        output_json=tmp_path / "out.json",
    )

    page_response = MagicMock()
    page_response.status_code = 200
    page_response.text = SAMPLE_HTML

    pdf_response = MagicMock()
    pdf_response.status_code = 200
    pdf_response.headers = {"Content-Type": "application/pdf", "Content-Length": "2048"}
    pdf_response.content = b"%PDF-1.4 minimal"

    with patch.object(scraper, "_warm_up_host"), patch.object(
            scraper._session, "get", return_value=page_response
    ), patch(
        "app.tasks.scraping.scraper.download_pdf",
        return_value=(b"%PDF-1.4", 2.0),
    ), patch(
        "app.tasks.scraping.scraper.extract_pdf_text",
        return_value="Sample extracted PDF text content.",
    ), patch.object(scraper, "_delay_between_requests"):
        docs = scraper._scrape_target(
            ScrapeTarget(page_url="https://example.com/news/", html=SAMPLE_HTML)
        )

    assert len(docs) == 3
    assert docs[0].document_type == "PDF"
    assert docs[0].content_preview.startswith("Sample extracted")
    assert docs[0].size_kb == 2.0


def test_scrape_page_skips_failed_pdf_download(tmp_path):
    """A failed PDF download is logged and other PDFs still process."""
    scraper = DocumentScraper(
        urls_file=tmp_path / "urls.txt",
        output_json=tmp_path / "out.json",
    )

    page_response = MagicMock()
    page_response.status_code = 200
    page_response.text = SAMPLE_HTML

    with patch.object(scraper, "_warm_up_host"), patch.object(
            scraper._session, "get", return_value=page_response
    ), patch(
        "app.tasks.scraping.scraper.download_pdf",
        side_effect=ScrapingPDFError("bad pdf"),
    ), patch(
        "app.tasks.scraping.scraper.extract_pdf_text",
        return_value="text",
    ):
        docs = scraper._scrape_target(
            ScrapeTarget(page_url="https://example.com/news/", html=SAMPLE_HTML)
        )

    assert docs == []


def test_fetch_page_raises_on_timeout(tmp_path):
    """Page fetch timeouts surface as scraping failures via requests."""
    scraper = DocumentScraper(
        urls_file=tmp_path / "urls.txt",
        output_json=tmp_path / "out.json",
    )
    from app.tasks.scraping.exceptions import ScrapingPageError

    with patch.object(scraper, "_warm_up_host"), patch.object(
            scraper._page_fetcher,
            "fetch",
            side_effect=ScrapingPageError("Page request timed out"),
    ), pytest.raises(ScrapingPageError):
        scraper._fetch_page_html("https://example.com")


def test_fetch_page_reports_clear_403_message(tmp_path):
    """HTTP 403 responses raise a descriptive ScrapingPageError."""
    scraper = DocumentScraper(
        urls_file=tmp_path / "urls.txt",
        output_json=tmp_path / "out.json",
    )
    from app.tasks.scraping.exceptions import ScrapingPageError

    with patch.object(scraper, "_warm_up_host"), patch.object(
            scraper._page_fetcher,
            "fetch",
            side_effect=ScrapingPageError("Access forbidden (403)"),
    ), pytest.raises(ScrapingPageError, match="403"):
        scraper._fetch_page_html("https://www.minfin.bg/bg/1394")


def test_extract_pdf_text_raises_on_invalid_bytes():
    """Invalid PDF bytes raise ScrapingPDFError during text extraction."""
    with pytest.raises(ScrapingPDFError):
        extract_pdf_text(b"not-a-pdf")
