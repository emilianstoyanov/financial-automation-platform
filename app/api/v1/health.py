"""Health check endpoints."""

from sqlalchemy import text
from app.core.config import Settings
from fastapi import APIRouter, Depends
from app.schemas.health import HealthResponse
from app.api.deps import DbSession, get_settings_dep

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check(
        db: DbSession,
        settings: Settings = Depends(get_settings_dep),
) -> HealthResponse:
    """Versioned health check with database connectivity probe."""
    db_status = "unknown"
    try:
        db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception:
        db_status = "disconnected"

    return HealthResponse(
        status="healthy" if db_status == "connected" else "degraded",
        environment=settings.environment,
        service=settings.app_name,
        database=db_status,
        version="0.1.0",
        news_scheduler_enabled=settings.news_scheduler_enabled,
        news_scheduler_interval_minutes=settings.news_scheduler_interval_minutes,
        rates_scheduler_enabled=settings.rates_scheduler_enabled,
        rates_scheduler_interval_minutes=settings.rates_scheduler_interval_minutes,
    )
