"""Repository for app_metadata key/value rows."""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.metadata import AppMetadata


class MetadataRepository:
    """Read and write key/value metadata."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def set(self, key: str, value: str) -> None:
        """Insert or update a metadata entry."""
        now = datetime.now(timezone.utc)
        row = self._session.get(AppMetadata, key)
        if row is None:
            row = AppMetadata(key=key, value=value, updated_at=now)
            self._session.add(row)
        else:
            row.value = value
            row.updated_at = now
        self._session.flush()

    def get(self, key: str) -> str | None:
        row = self._session.get(AppMetadata, key)
        return row.value if row else None

    def get_many(self, keys: list[str]) -> dict[str, str | None]:
        if not keys:
            return {}
        stmt = select(AppMetadata).where(AppMetadata.key.in_(keys))
        rows = self._session.scalars(stmt).all()
        found = {row.key: row.value for row in rows}
        return {key: found.get(key) for key in keys}
