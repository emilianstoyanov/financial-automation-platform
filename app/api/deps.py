"""FastAPI dependencies shared across route modules."""

from fastapi import Depends
from typing import Annotated
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.config import Settings, get_settings

DbSession = Annotated[Session, Depends(get_db)]


def get_settings_dep() -> Settings:
    """Inject application settings."""
    return get_settings()
