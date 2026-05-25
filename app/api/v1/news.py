"""Financial news API endpoints (Task 5)."""

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import DbSession
from app.schemas.news import NewsItemResponse, NewsListResponse, NewsRefreshResponse
from app.services.news_service import NewsApplicationService
from app.tasks.news.constants import DEFAULT_NEWS_LIMIT, MAX_NEWS_LIMIT

router = APIRouter(prefix="/news", tags=["News"])


def _article_to_response(article) -> NewsItemResponse:
    data = NewsApplicationService.to_item_dict(article)
    return NewsItemResponse(**data)


@router.get("", response_model=NewsListResponse)
async def list_news(
    db: DbSession,
    limit: int = Query(DEFAULT_NEWS_LIMIT, ge=1, le=MAX_NEWS_LIMIT),
) -> NewsListResponse:
    """Return latest saved news items from SQLite."""
    service = NewsApplicationService(db)
    articles, total = service.list_news(limit=limit)
    metadata = service.get_refresh_metadata()
    return NewsListResponse(
        total=total,
        items=[_article_to_response(article) for article in articles],
        **metadata,
    )


@router.post("/refresh", response_model=NewsRefreshResponse)
async def refresh_news(db: DbSession) -> NewsRefreshResponse:
    """Fetch configured RSS feeds and save only new unique items."""
    service = NewsApplicationService(db)

    try:
        result = service.refresh()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"News refresh failed: {exc}",
        ) from exc

    preview = [
        NewsItemResponse(**NewsApplicationService.news_item_to_dict(item))
        for item in result.new_items[:10]
    ]

    metadata = service.metadata_from_result(result)
    return NewsRefreshResponse(
        inserted_count=result.inserted_count,
        skipped_duplicates=result.skipped_duplicates,
        errors=result.errors,
        preview=preview,
        **metadata,
    )
