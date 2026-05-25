"""Local dashboard routes (Jinja2 + static assets)."""

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.core.config import get_settings
from app.tasks.news.constants import news_feed_source_entries

_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))

router = APIRouter(include_in_schema=False)


@router.get("/", response_class=HTMLResponse, name="dashboard")
async def dashboard(request: Request) -> HTMLResponse:
    """Render the local operations dashboard."""
    settings = get_settings()
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "request": request,
            "app_name": settings.app_name,
            "api_prefix": settings.api_v1_prefix,
            "news_rss_sources": news_feed_source_entries(settings.news_rss_feeds),
        },
    )
