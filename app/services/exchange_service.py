"""Service layer for exchange rate operations."""

from pathlib import Path
from app.core.config import get_settings
from app.tasks.exchange.client import ExchangeRateClient
from app.tasks.exchange.constants import DEFAULT_CACHE_FILE
from app.tasks.exchange.models import ConversionResult, ExchangeRatesResult


class ExchangeApplicationService:
    """Thin wrapper around ``ExchangeRateClient`` for FastAPI handlers."""

    def __init__(self, cache_file: str | Path = DEFAULT_CACHE_FILE) -> None:
        settings = get_settings()
        self._client = ExchangeRateClient(
            cache_file=cache_file,
            api_url=settings.exchange_rate_api_url,
        )

    def get_rates(self) -> ExchangeRatesResult:
        """Return EUR, USD, and GBP rates against BGN."""
        return self._client.get_rates()

    def convert(
            self,
            from_currency: str,
            to_currency: str,
            amount: float,
    ) -> ConversionResult:
        """Convert ``amount`` between supported currencies."""
        return self._client.convert(from_currency, to_currency, amount)
