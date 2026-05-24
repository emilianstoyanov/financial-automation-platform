"""SQLAlchemy ORM models.

Import all models here so Alembic/metadata discovery can register them.
"""

from app.core.database import Base

__all__ = ["Base"]
