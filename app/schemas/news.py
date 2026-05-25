"""News API schemas."""

from pydantic import BaseModel, Field


class NewsItemResponse(BaseModel):
    """Single news article."""

    id: int | None = None
    title: str
    url: str
    summary: str
    source: str
    published_at: str | None = None
    collected_at: str


class NewsListResponse(BaseModel):
    """Latest news list."""

    total: int
    items: list[NewsItemResponse]
    last_refresh_at: str | None = None
    last_inserted_count: int | None = None
    last_skipped_duplicates: int | None = None
    last_warning_count: int | None = None
    last_warning_summary: str | None = None


class NewsRefreshResponse(BaseModel):
    """Result of refreshing RSS feeds."""

    inserted_count: int
    skipped_duplicates: int
    errors: list[dict[str, str]] = Field(default_factory=list)
    preview: list[NewsItemResponse] = Field(
        default_factory=list,
        description="Newly inserted items from this refresh",
    )
    last_refresh_at: str | None = None
    last_inserted_count: int | None = None
    last_skipped_duplicates: int | None = None
    last_warning_count: int | None = None
    last_warning_summary: str | None = None
