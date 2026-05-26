"""Document scraping API endpoint tests."""

from unittest.mock import patch

from app.tasks.scraping.models import ScrapedDocument, ScrapingResult
from app.tasks.scraping.warnings import SCRAPE_INVALID_OR_UNREACHABLE_URL_MESSAGE


def _sample_result() -> ScrapingResult:
    doc = ScrapedDocument(
        title="Report",
        url="https://example.com/report.pdf",
        size_kb=100.0,
        date_published="2024-01-01",
        document_type="PDF",
        content_preview="Preview text",
        scraped_at="2026-05-23T10:00:00+00:00",
        source_page="https://example.com",
    )
    return ScrapingResult(status="success", documents=[doc])


def test_process_local_urls_endpoint(client):
    """GET process-local-urls returns status and document preview."""
    with patch(
        "app.api.v1.scraping.ScrapingApplicationService.process_local_urls",
        return_value=_sample_result(),
    ):
        response = client.get("/api/v1/scraping/process-local-urls")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["total_documents"] == 1
    assert len(data["documents"]) == 1


def test_scrape_url_endpoint(client):
    """POST scrape-url accepts JSON url and returns extracted documents."""
    with patch(
        "app.api.v1.scraping.ScrapingApplicationService.scrape_url",
        return_value=_sample_result(),
    ):
        response = client.post(
            "/api/v1/scraping/scrape-url",
            json={"url": "https://example.com/page"},
        )

    assert response.status_code == 200
    assert response.json()["total_documents"] == 1


def test_scrape_url_rejects_invalid_url(client):
    """POST scrape-url returns 422 for a Pydantic-invalid URL body."""
    response = client.post(
        "/api/v1/scraping/scrape-url",
        json={"url": "not-a-valid-url"},
    )
    assert response.status_code == 422


def test_scrape_url_maps_failed_result_errors(client):
    """POST scrape-url maps unreachable hosts to a friendly error message."""
    with patch(
        "app.api.v1.scraping.ScrapingApplicationService.scrape_url",
        return_value=ScrapingResult(
            status="failed",
            documents=[],
            errors=["http://bad.example: Page request failed: timeout"],
        ),
    ):
        response = client.post(
            "/api/v1/scraping/scrape-url",
            json={"url": "https://bad.example/page"},
        )

    assert response.status_code == 200
    assert response.json()["errors"] == [SCRAPE_INVALID_OR_UNREACHABLE_URL_MESSAGE]
