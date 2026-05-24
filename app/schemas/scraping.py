"""Document scraping API schemas."""

from pydantic import BaseModel, Field, HttpUrl


class ScrapeUrlRequest(BaseModel):
    """Request body for scraping a single page."""

    url: HttpUrl


class ScrapeHtmlRequest(BaseModel):
    """HTML saved from a browser plus the canonical page URL for link resolution."""

    page_url: HttpUrl
    html: str = Field(min_length=1, description="Full or partial HTML from the page")


class ScrapingProcessResponse(BaseModel):
    """Response for a scraping run."""

    status: str
    total_documents: int
    documents: list[dict] = Field(
        default_factory=list,
        description="Preview of scraped documents (up to 10)",
    )
    errors: list[str] = Field(default_factory=list)
