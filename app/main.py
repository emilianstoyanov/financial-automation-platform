"""FastAPI application entry point."""

from fastapi import FastAPI
from app.api.router import api_router
from app.core.database import init_db
from app.core.config import get_settings
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from app.core.swagger_ui import setup_swagger_ui
from fastapi.middleware.cors import CORSMiddleware
from app.core.static_files import mount_static_files
from app.core.data_dirs import ensure_data_directories
from app.web.dashboard import router as dashboard_router
from app.core.logging_config import get_logger, setup_logging

settings = get_settings()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Application startup and shutdown hooks."""
    setup_logging(settings)
    logger.info("Starting %s [%s]", settings.app_name, settings.environment)

    ensure_data_directories()
    init_db()
    logger.info("Database initialized")

    yield

    logger.info("Shutting down %s", settings.app_name)


def create_app() -> FastAPI:
    """Application factory for FastAPI and ASGI servers."""
    openapi_url = "/openapi.json" if settings.openapi_enabled else None
    redoc_url = "/redoc" if settings.openapi_enabled else None

    application = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="Financial automation platform API — ETL, exchange rates, scraping, and LLM pipelines.",
        lifespan=lifespan,
        debug=settings.debug,
        openapi_url=openapi_url,
        docs_url=None,
        redoc_url=redoc_url,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.is_development else [],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    application.include_router(api_router, prefix=settings.api_v1_prefix)
    mount_static_files(application)
    application.include_router(dashboard_router)
    setup_swagger_ui(application, settings)

    return application


app = create_app()
