"""Shared static file mounting for Swagger UI and dashboard."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

_STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


def mount_static_files(application: FastAPI) -> None:
    """Serve ``app/static`` at ``/static`` (CSS for docs and dashboard)."""
    application.mount(
        "/static",
        StaticFiles(directory=_STATIC_DIR),
        name="static",
    )
