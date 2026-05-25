"""Exchange rate history service for Task 5 SQLite storage."""

from dataclasses import dataclass, field
from datetime import date, datetime, timezone

from sqlalchemy.orm import Session

from app.core.logging_config import get_logger
from app.repositories.exchange_rate_repository import ExchangeRateRepository
from app.repositories.metadata_repository import MetadataRepository
from app.services.exchange_service import ExchangeApplicationService
from app.tasks.exchange.constants import DEFAULT_BASE_CURRENCY, TARGET_CURRENCIES
from app.tasks.exchange.exceptions import ExchangeError
from app.tasks.exchange.metadata_keys import (
    RATES_LAST_INSERTED_COUNT,
    RATES_LAST_REFRESH_AT,
    RATES_LAST_SOURCE,
    RATES_LAST_UPDATED_COUNT,
)
from app.tasks.exchange.models import ExchangeRatesResult

logger = get_logger(__name__)


@dataclass
class RatesRefreshResult:
    """Result of refreshing and persisting exchange rates."""

    inserted_count: int = 0
    updated_count: int = 0
    source: str = ""
    rate_date: date | None = None
    errors: list[dict[str, str]] = field(default_factory=list)


class RatesHistoryApplicationService:
    """Fetch live rates (Task 2 client) and persist daily history in SQLite."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._repository = ExchangeRateRepository(session)
        self._metadata = MetadataRepository(session)
        self._exchange = ExchangeApplicationService()
        self._base = DEFAULT_BASE_CURRENCY

    def refresh(self) -> RatesRefreshResult:
        """Fetch current rates and upsert today's snapshot into SQLite."""
        result = RatesRefreshResult()
        logger.info("Exchange rates history refresh started")

        try:
            live: ExchangeRatesResult = self._exchange.get_rates()
        except ExchangeError as exc:
            result.errors.append({"source": "exchange_api", "error": str(exc)})
            logger.error("Exchange rates fetch failed: %s", exc)
            return result
        except Exception as exc:
            result.errors.append({"source": "exchange_api", "error": str(exc)})
            logger.exception("Unexpected exchange rates fetch error")
            return result

        rate_date = self._rate_date_from_timestamp(live.timestamp)
        collected_at = datetime.now(timezone.utc)
        rows: list[dict] = []

        for code in TARGET_CURRENCIES:
            rate = live.bgn_per_unit.get(code)
            if rate is None:
                result.errors.append(
                    {"source": code, "error": f"Missing rate for {code}"},
                )
                continue
            if not self._is_valid_rate(rate):
                result.errors.append(
                    {"source": code, "error": f"Invalid rate for {code}: {rate}"},
                )
                continue
            rows.append(
                {
                    "base_currency": self._base,
                    "target_currency": code,
                    "rate": round(rate, 6),
                    "rate_date": rate_date,
                    "collected_at": collected_at,
                    "source": live.source,
                }
            )

        if rows:
            inserted, updated = self._repository.save_rates(rows)
            result.inserted_count = inserted
            result.updated_count = updated
            result.source = live.source
            result.rate_date = rate_date
            self._persist_refresh_metadata(result, collected_at.isoformat())

        try:
            self._session.commit()
        except Exception as exc:
            self._session.rollback()
            logger.exception("Database error during exchange rates refresh")
            result.errors.append({"source": "database", "error": str(exc)})
            raise

        logger.info(
            "Exchange rates history refresh finished: inserted=%d updated=%d source=%s",
            result.inserted_count,
            result.updated_count,
            result.source,
        )
        return result

    def get_latest_with_changes(self) -> dict:
        """Latest stored rates with daily change vs previous day."""
        metadata = self.get_refresh_metadata()
        records = self._repository.get_latest_rates(self._base)
        rates = [self._record_to_dict(record, include_change=True) for record in records]
        return {
            "base_currency": self._base,
            "rates": rates,
            "errors": [],
            **metadata,
        }

    def get_history(self, days: int = 7) -> dict:
        records = self._repository.get_history(self._base, days)
        return {
            "base_currency": self._base,
            "days": max(1, min(days, 365)),
            "history": [self._record_to_dict(record, include_change=False) for record in records],
            **self.get_refresh_metadata(),
        }

    def get_refresh_metadata(self) -> dict[str, str | int | None]:
        raw = self._metadata.get_many(
            [
                RATES_LAST_REFRESH_AT,
                RATES_LAST_SOURCE,
                RATES_LAST_INSERTED_COUNT,
                RATES_LAST_UPDATED_COUNT,
            ]
        )
        return {
            "last_refresh_at": raw[RATES_LAST_REFRESH_AT],
            "source": raw[RATES_LAST_SOURCE],
            "last_inserted_count": self._parse_int(raw[RATES_LAST_INSERTED_COUNT]),
            "last_updated_count": self._parse_int(raw[RATES_LAST_UPDATED_COUNT]),
        }

    def build_response_from_refresh(self, refresh: RatesRefreshResult) -> dict:
        latest = self.get_latest_with_changes()
        latest["last_inserted_count"] = refresh.inserted_count
        latest["last_updated_count"] = refresh.updated_count
        if refresh.errors:
            latest["errors"] = refresh.errors
        return latest

    def _record_to_dict(
        self,
        record,
        *,
        include_change: bool,
    ) -> dict:
        data = {
            "target_currency": record.target_currency,
            "rate": record.rate,
            "rate_date": record.rate_date.isoformat(),
            "collected_at": record.collected_at.isoformat(),
            "source": record.source,
            "daily_change": None,
            "daily_change_pct": None,
        }
        if include_change:
            previous = self._repository.get_previous_rate(
                record.base_currency,
                record.target_currency,
                record.rate_date,
            )
            if previous is not None:
                change = round(record.rate - previous.rate, 6)
                data["daily_change"] = change
                if previous.rate:
                    data["daily_change_pct"] = round(
                        (change / previous.rate) * 100,
                        4,
                    )
        return data

    def _persist_refresh_metadata(
        self,
        result: RatesRefreshResult,
        collected_at: str,
    ) -> None:
        self._metadata.set(RATES_LAST_REFRESH_AT, collected_at)
        self._metadata.set(RATES_LAST_SOURCE, result.source or "")
        self._metadata.set(RATES_LAST_INSERTED_COUNT, str(result.inserted_count))
        self._metadata.set(RATES_LAST_UPDATED_COUNT, str(result.updated_count))

    @staticmethod
    def _rate_date_from_timestamp(timestamp: str) -> date:
        try:
            parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.date()
        except ValueError:
            return datetime.now(timezone.utc).date()

    @staticmethod
    def _is_valid_rate(rate: float) -> bool:
        return isinstance(rate, (int, float)) and rate > 0

    @staticmethod
    def _parse_int(value: str | None) -> int | None:
        if value is None:
            return None
        try:
            return int(value)
        except ValueError:
            return None
