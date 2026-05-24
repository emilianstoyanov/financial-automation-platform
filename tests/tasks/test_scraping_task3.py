"""Task 3 integration-style unit tests: JSON output, logging, and error handling."""

import json
from unittest.mock import patch
from app.tasks.scraping.scraper import DocumentScraper
import app.tasks.scraping.logging_setup as logging_setup
from app.tasks.scraping.constants import PREVIEW_MAX_CHARS
from app.tasks.scraping.exceptions import ScrapingPageError
from app.tasks.scraping.models import ScrapedDocument, ScrapingResult
from app.tasks.scraping.parsers import PdfLinkCandidate, ScrapeTarget

SAMPLE_HTML = """
<html><body>
  <a href="https://example.com/report.pdf">Annual Report 2024</a>
  <time datetime="2024-03-15"></time>
</body></html>
"""


def test_json_output_structure(tmp_path):
    """Saved JSON includes metadata, documents array, and errors list."""
    output = tmp_path / "extracted_documents.json"
    scraper = DocumentScraper(
        urls_file=tmp_path / "urls.txt",
        output_json=output,
    )
    document = ScrapedDocument(
        title="Annual Report 2024",
        url="https://example.com/report.pdf",
        size_kb=10.0,
        date_published="2024-03-15",
        document_type="PDF",
        content_preview="Preview",
        scraped_at="2026-05-23T12:00:00+00:00",
        source_page="https://example.com/news/",
    )
    scraper._save_results(ScrapingResult(status="success", documents=[document]))

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert set(payload.keys()) == {"metadata", "documents", "errors"}
    assert payload["metadata"]["total_documents"] == 1
    assert payload["documents"][0]["title"] == "Annual Report 2024"
    assert payload["documents"][0]["url"] == "https://example.com/report.pdf"
    assert payload["errors"] == []


def test_content_preview_limited_to_500_characters(tmp_path):
    """Extracted preview is capped at PREVIEW_MAX_CHARS (500 per assignment)."""
    scraper = DocumentScraper(
        urls_file=tmp_path / "urls.txt",
        output_json=tmp_path / "out.json",
    )
    candidate = PdfLinkCandidate(
        url="https://example.com/long.pdf",
        title="Long doc",
        date_published=None,
    )
    long_text = "Текст " * 300

    with patch(
            "app.tasks.scraping.scraper.download_pdf",
            return_value=(b"%PDF-1.4", 1.0),
    ), patch(
        "app.tasks.scraping.scraper.extract_pdf_text",
        return_value=long_text,
    ):
        doc = scraper._process_pdf(candidate, "https://example.com/page")

    assert len(doc.content_preview) == PREVIEW_MAX_CHARS


def test_process_targets_handles_blocked_page_gracefully(tmp_path):
    """A blocked page is recorded in errors; other targets still run."""
    scraper = DocumentScraper(
        urls_file=tmp_path / "urls.txt",
        output_json=tmp_path / "out.json",
    )
    ok_doc = ScrapedDocument(
        title="Annual Report 2024",
        url="https://example.com/report.pdf",
        size_kb=1.0,
        date_published="2024-03-15",
        document_type="PDF",
        content_preview="x",
        scraped_at="2026-05-23T12:00:00+00:00",
        source_page="https://example.com/ok",
    )

    with patch.object(
            scraper,
            "_scrape_target",
            side_effect=[
                ScrapingPageError("Access blocked by Cloudflare"),
                [ok_doc],
            ],
    ), patch.object(scraper, "_delay_between_requests"):
        result = scraper.process_targets(
            [
                ScrapeTarget(page_url="https://www.minfin.bg/bg/1394"),
                ScrapeTarget(page_url="https://example.com/ok", html=SAMPLE_HTML),
            ],
            persist=False,
        )

    assert result.status == "success"
    assert len(result.errors) == 1
    assert "minfin.bg" in result.errors[0]
    assert result.total_documents == 1
    assert result.documents[0].date_published == "2024-03-15"


def test_scraping_log_contains_start_and_finish(tmp_path, monkeypatch):
    """Scraping run writes start/end lines to the configured log file."""
    monkeypatch.setattr(logging_setup, "_CONFIGURED", False)
    log_path = tmp_path / "scraping.log"
    scraper = DocumentScraper(
        urls_file=tmp_path / "urls.txt",
        output_json=tmp_path / "out.json",
        log_file=str(log_path),
    )

    with patch(
            "app.tasks.scraping.scraper.download_pdf",
            return_value=(b"%PDF-1.4", 1.0),
    ), patch(
        "app.tasks.scraping.scraper.extract_pdf_text",
        return_value="Sample text",
    ):
        scraper.process_targets(
            [ScrapeTarget(page_url="https://example.com/p", html=SAMPLE_HTML)],
            persist=False,
        )

    log_text = log_path.read_text(encoding="utf-8")
    assert "Scraping started" in log_text
    assert "Scraping finished" in log_text
    assert "PDF link:" in log_text
    assert "Downloaded PDF" in log_text
