"""Document scraping exceptions."""


class ScrapingError(Exception):
    """Base exception for scraping operations."""


class ScrapingInvalidURLError(ScrapingError):
    """Raised when a URL is missing or malformed."""


class ScrapingPageError(ScrapingError):
    """Raised when a page cannot be fetched (404, timeout, etc.)."""


class ScrapingPDFError(ScrapingError):
    """Raised when a PDF cannot be downloaded or parsed."""
