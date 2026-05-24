"""Document scraping API endpoints."""

from app.schemas.scraping import (
    ScrapeHtmlRequest,
    ScrapeUrlRequest,
    ScrapingProcessResponse,
)
from fastapi import APIRouter, HTTPException, status
from app.tasks.scraping.models import ScrapingResult
from app.services.scraping_service import ScrapingApplicationService
from app.tasks.scraping.exceptions import (
    ScrapingInvalidURLError,
    ScrapingPageError,
)

router = APIRouter(prefix="/scraping", tags=["Scraping"])


def _build_response(result: ScrapingResult) -> ScrapingProcessResponse:
    """Map scraping result to API response with document preview."""
    return ScrapingProcessResponse(
        status=result.status,
        total_documents=result.total_documents,
        documents=result.preview,
        errors=result.errors,
    )


@router.get(
    "/process-local-urls",
    response_model=ScrapingProcessResponse,
    summary="Scrape URLs from sample_urls.txt",
)
async def process_local_urls() -> ScrapingProcessResponse:
    """Scrape every URL in ``data/scraping/sample_urls.txt``; write JSON and log file."""
    service = ScrapingApplicationService()

    try:
        result = service.process_local_urls(persist=True)
    except ScrapingInvalidURLError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return _build_response(result)


@router.post(
    "/scrape-url",
    response_model=ScrapingProcessResponse,
    summary="Scrape PDF links from one URL",
)
async def scrape_url(body: ScrapeUrlRequest) -> ScrapingProcessResponse:
    """Scrape a single page URL; saves results to ``extracted_documents.json``."""
    service = ScrapingApplicationService()

    try:
        result = service.scrape_url(str(body.url), persist=True)
    except ScrapingInvalidURLError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except ScrapingPageError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    return _build_response(result)


@router.post(
    "/scrape-html",
    response_model=ScrapingProcessResponse,
    summary="Scrape PDF links from saved HTML",
)
async def scrape_html(body: ScrapeHtmlRequest) -> ScrapingProcessResponse:
    """Scrape PDFs from browser-saved HTML; write ``extracted_documents.json``."""
    service = ScrapingApplicationService()

    try:
        result = service.scrape_html(
            body.html,
            str(body.page_url),
            persist=True,
        )
    except ScrapingInvalidURLError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return _build_response(result)
