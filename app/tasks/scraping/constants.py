"""Document scraping constants."""

from typing import Final
from app.core.data_dirs import SCRAPING_DATA_DIR

DEFAULT_URLS_FILE: Final[str] = str(SCRAPING_DATA_DIR / "sample_urls.txt")
DEFAULT_OUTPUT_JSON: Final[str] = str(SCRAPING_DATA_DIR / "extracted_documents.json")
DEFAULT_SCRAPING_LOG: Final[str] = "logs/scraping.log"

USER_AGENT: Final[str] = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
MIN_PDFS_PER_PAGE: Final[int] = 3
MAX_PDFS_PER_PAGE: Final[int] = 20
PREVIEW_MAX_CHARS: Final[int] = 500
REQUEST_TIMEOUT_SECONDS: Final[int] = 30
PLAYWRIGHT_NAVIGATION_TIMEOUT_MS: Final[int] = 120_000
PLAYWRIGHT_NETWORK_IDLE_TIMEOUT_MS: Final[int] = 30_000
MIN_DELAY_SECONDS: Final[float] = 1.0
MAX_DELAY_SECONDS: Final[float] = 2.0
DOCUMENT_TYPE_PDF: Final[str] = "PDF"
