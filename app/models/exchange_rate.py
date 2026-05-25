"""Historical exchange rate ORM model (Task 5)."""

from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ExchangeRateRecord(Base):
    """Daily BGN-based FX rate snapshot stored in SQLite."""

    __tablename__ = "exchange_rates"
    __table_args__ = (
        UniqueConstraint(
            "base_currency",
            "target_currency",
            "rate_date",
            name="uq_exchange_rates_currency_date",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    base_currency: Mapped[str] = mapped_column(String(3), nullable=False)
    target_currency: Mapped[str] = mapped_column(String(3), nullable=False)
    rate: Mapped[float] = mapped_column(Float, nullable=False)
    rate_date: Mapped[date] = mapped_column(Date, nullable=False)
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
