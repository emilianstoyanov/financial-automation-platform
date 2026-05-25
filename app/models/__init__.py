"""SQLAlchemy ORM models.

Import all models here so Alembic/metadata discovery can register them.
"""

from app.core.database import Base
from app.models.exchange_rate import ExchangeRateRecord
from app.models.metadata import AppMetadata
from app.models.news import NewsArticle

__all__ = ["Base", "AppMetadata", "ExchangeRateRecord", "NewsArticle"]
