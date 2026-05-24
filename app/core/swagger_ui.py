"""Custom Swagger UI with project styling."""

from fastapi import FastAPI
from app.core.config import Settings
from fastapi.responses import HTMLResponse
from fastapi.openapi.docs import get_swagger_ui_html


def setup_swagger_ui(application: FastAPI, settings: Settings) -> None:
    """Register a styled Swagger UI at /docs (static assets mounted separately)."""
    if not settings.openapi_enabled:
        return

    @application.get("/docs", include_in_schema=False)
    async def swagger_ui() -> HTMLResponse:
        html_response = get_swagger_ui_html(
            openapi_url=application.openapi_url,
            title=f"{settings.app_name} - API Docs",
            swagger_ui_parameters={"displayRequestDuration": True},
        )
        custom_head = (
            '<link rel="stylesheet" type="text/css" '
            'href="/static/swagger-custom.css?v=2" />'
            '<script src="/static/swagger-custom.js?v=2"></script>'
        )
        body = html_response.body.decode("utf-8")
        body = body.replace("</head>", f"{custom_head}</head>", 1)
        return HTMLResponse(content=body, status_code=html_response.status_code)
