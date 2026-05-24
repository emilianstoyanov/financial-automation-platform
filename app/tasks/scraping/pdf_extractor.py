"""PDF download and text extraction."""

import io
import requests
from PyPDF2 import PdfReader
from app.tasks.scraping.constants import REQUEST_TIMEOUT_SECONDS
from app.tasks.scraping.exceptions import ScrapingPDFError
from app.tasks.scraping.http_session import PDF_ACCEPT, build_browser_headers


def download_pdf(
        url: str,
        session: requests.Session,
        referer: str | None = None,
) -> tuple[bytes, float | None]:
    """Fetch PDF bytes; return size in KB when ``Content-Length`` is present."""
    headers = build_browser_headers(referer=referer, accept=PDF_ACCEPT, navigation=False)
    try:
        response = session.get(
            url,
            timeout=REQUEST_TIMEOUT_SECONDS,
            stream=True,
            headers=headers,
        )
    except requests.Timeout as exc:
        raise ScrapingPDFError(f"PDF download timed out: {url}") from exc
    except requests.RequestException as exc:
        raise ScrapingPDFError(f"PDF download failed: {url}") from exc

    if response.status_code == 403:
        raise ScrapingPDFError(f"PDF access forbidden (403): {url}")
    if response.status_code >= 400:
        raise ScrapingPDFError(f"PDF HTTP {response.status_code}: {url}")

    content_type = response.headers.get("Content-Type", "").lower()
    if "pdf" not in content_type and not url.lower().split("?")[0].endswith(".pdf"):
        if "octet-stream" not in content_type:
            raise ScrapingPDFError(f"URL is not a PDF: {url}")

    data = response.content
    size_kb = None
    content_length = response.headers.get("Content-Length")
    if content_length and content_length.isdigit():
        size_kb = round(int(content_length) / 1024, 2)
    elif data:
        size_kb = round(len(data) / 1024, 2)

    return data, size_kb


def extract_pdf_text(data: bytes) -> str:
    """Extract plain text from PDF bytes using PyPDF2."""
    try:
        reader = PdfReader(io.BytesIO(data))
        parts: list[str] = []
        for page in reader.pages:
            page_text = page.extract_text() or ""
            parts.append(page_text)
        text = "\n".join(parts).strip()
    except Exception as exc:
        raise ScrapingPDFError("Failed to extract text from PDF") from exc

    if not text:
        raise ScrapingPDFError("PDF contains no extractable text")
    return text
