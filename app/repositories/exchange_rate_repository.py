"""Repository for historical exchange rates."""

from datetime import date, datetime, timedelta, timezone

from sqlalchemy import and_, desc, select
from sqlalchemy.orm import Session

from app.models.exchange_rate import ExchangeRateRecord
from app.repositories.base import BaseRepository


class ExchangeRateRepository(BaseRepository[ExchangeRateRecord]):
    """Persistence for BGN-based daily exchange rate snapshots."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, ExchangeRateRecord)

    def upsert_rate(
        self,
        *,
        base_currency: str,
        target_currency: str,
        rate: float,
        rate_date: date,
        collected_at: datetime,
        source: str,
    ) -> tuple[ExchangeRateRecord, bool]:
        """Insert or update a rate row. Returns (entity, inserted) where inserted is True for new rows."""
        stmt = select(ExchangeRateRecord).where(
            ExchangeRateRecord.base_currency == base_currency,
            ExchangeRateRecord.target_currency == target_currency,
            ExchangeRateRecord.rate_date == rate_date,
        )
        existing = self._session.scalar(stmt)

        if existing is None:
            entity = ExchangeRateRecord(
                base_currency=base_currency,
                target_currency=target_currency,
                rate=rate,
                rate_date=rate_date,
                collected_at=collected_at,
                source=source,
            )
            self.add(entity)
            return entity, True

        existing.rate = rate
        existing.collected_at = collected_at
        existing.source = source
        self._session.flush()
        return existing, False

    def save_rates(
        self,
        rows: list[dict],
    ) -> tuple[int, int]:
        """Upsert multiple rates; returns (inserted_count, updated_count)."""
        inserted = 0
        updated = 0
        for row in rows:
            _, is_new = self.upsert_rate(
                base_currency=row["base_currency"],
                target_currency=row["target_currency"],
                rate=row["rate"],
                rate_date=row["rate_date"],
                collected_at=row["collected_at"],
                source=row["source"],
            )
            if is_new:
                inserted += 1
            else:
                updated += 1
        return inserted, updated

    def get_latest_rate_date(self, base_currency: str) -> date | None:
        stmt = (
            select(ExchangeRateRecord.rate_date)
            .where(ExchangeRateRecord.base_currency == base_currency)
            .order_by(desc(ExchangeRateRecord.rate_date))
            .limit(1)
        )
        return self._session.scalar(stmt)

    def get_latest_rates(self, base_currency: str) -> list[ExchangeRateRecord]:
        latest_date = self.get_latest_rate_date(base_currency)
        if latest_date is None:
            return []
        stmt = (
            select(ExchangeRateRecord)
            .where(
                ExchangeRateRecord.base_currency == base_currency,
                ExchangeRateRecord.rate_date == latest_date,
            )
            .order_by(ExchangeRateRecord.target_currency)
        )
        return list(self._session.scalars(stmt).all())

    def get_history(self, base_currency: str, days: int) -> list[ExchangeRateRecord]:
        days = max(1, min(days, 365))
        cutoff = datetime.now(timezone.utc).date() - timedelta(days=days - 1)
        stmt = (
            select(ExchangeRateRecord)
            .where(
                ExchangeRateRecord.base_currency == base_currency,
                ExchangeRateRecord.rate_date >= cutoff,
            )
            .order_by(desc(ExchangeRateRecord.rate_date), ExchangeRateRecord.target_currency)
        )
        return list(self._session.scalars(stmt).all())

    def get_previous_rate(
        self,
        base_currency: str,
        target_currency: str,
        before_date: date,
    ) -> ExchangeRateRecord | None:
        stmt = (
            select(ExchangeRateRecord)
            .where(
                ExchangeRateRecord.base_currency == base_currency,
                ExchangeRateRecord.target_currency == target_currency,
                ExchangeRateRecord.rate_date < before_date,
            )
            .order_by(desc(ExchangeRateRecord.rate_date))
            .limit(1)
        )
        return self._session.scalar(stmt)
