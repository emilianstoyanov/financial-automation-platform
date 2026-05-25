"""Exchange rate history API schemas (Task 5)."""

from pydantic import BaseModel, Field


class RateEntryResponse(BaseModel):
    """Single stored FX rate with optional daily change."""

    target_currency: str
    rate: float
    rate_date: str
    collected_at: str
    source: str
    daily_change: float | None = None
    daily_change_pct: float | None = None


class RatesLatestResponse(BaseModel):
    """Latest stored rates from SQLite."""

    base_currency: str
    rates: list[RateEntryResponse]
    last_refresh_at: str | None = None
    source: str | None = None
    last_inserted_count: int | None = None
    last_updated_count: int | None = None
    errors: list[dict[str, str]] = Field(default_factory=list)


class RatesHistoryResponse(BaseModel):
    """Historical rates for the last N days."""

    base_currency: str
    days: int
    history: list[RateEntryResponse]
    last_refresh_at: str | None = None
    source: str | None = None


class RatesRefreshResponse(RatesLatestResponse):
    """Result of refreshing and returning latest rates."""

    inserted_count: int = 0
    updated_count: int = 0
