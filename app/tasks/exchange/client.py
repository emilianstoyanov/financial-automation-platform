"""Exchange rate API client with caching, retries, and rate limiting."""

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

from app.core.config import get_settings
from app.core.data_dirs import ensure_data_directories
from app.core.logging_config import get_logger
from app.tasks.exchange.constants import (
    BACKOFF_BASE_SECONDS,
    CACHE_TTL_SECONDS,
    DEFAULT_BASE_CURRENCY,
    DEFAULT_CACHE_FILE,
    MAX_RETRIES,
    REQUEST_DELAY_SECONDS,
    REQUEST_TIMEOUT_SECONDS,
    SUPPORTED_CURRENCIES,
    TARGET_CURRENCIES,
)
from app.tasks.exchange.exceptions import (
    ExchangeAPIError,
    ExchangeCurrencyNotFoundError,
    ExchangeError,
    ExchangeInvalidResponseError,
    ExchangeNetworkError,
    ExchangeTimeoutError,
)
from app.tasks.exchange.models import ConversionResult, ExchangeRatesResult

logger = get_logger(__name__)


class ExchangeRateClient:
    """Fetch BGN-based FX rates from Exchangerate-API with JSON cache, retries, and conversion."""

    def __init__(
        self,
        base_currency: str = DEFAULT_BASE_CURRENCY,
        cache_file: str | Path = DEFAULT_CACHE_FILE,
        api_url: str | None = None,
        request_delay: float = REQUEST_DELAY_SECONDS,
        cache_ttl_seconds: int = CACHE_TTL_SECONDS,
    ) -> None:
        """Configure base currency, cache path, and request behavior."""
        self.base_currency = base_currency.upper()
        self.cache_file = Path(cache_file)
        self.api_url = api_url or get_settings().exchange_rate_api_url
        self.request_delay = request_delay
        self.cache_ttl_seconds = cache_ttl_seconds

    def get_rates(
        self,
        currencies: tuple[str, ...] | None = None,
    ) -> ExchangeRatesResult:
        """Return BGN-per-unit rates for ``currencies`` (default EUR, USD, GBP); uses cache if fresh."""
        requested = self._normalize_currencies(currencies or TARGET_CURRENCIES)
        payload, cached, source = self._get_rate_payload()
        return self._build_rates_result(payload, requested, cached, source)

    def convert(
        self,
        from_currency: str,
        to_currency: str,
        amount: float,
    ) -> ConversionResult:
        """Convert ``amount`` between BGN, EUR, USD, or GBP using cached or freshly fetched rates."""
        from_code = from_currency.upper()
        to_code = to_currency.upper()
        self._validate_currency(from_code)
        self._validate_currency(to_code)

        if amount < 0:
            raise ExchangeError("Amount must be non-negative")

        rates_result = self.get_rates(tuple(SUPPORTED_CURRENCIES - {self.base_currency}))
        converted, rate = self._convert_amount(
            amount,
            from_code,
            to_code,
            rates_result.rates_per_bgn,
        )

        return ConversionResult(
            from_currency=from_code,
            to_currency=to_code,
            original_amount=round(amount, 4),
            converted_amount=round(converted, 4),
            rate=round(rate, 6),
            source=rates_result.source,
            cached=rates_result.cached,
            timestamp=rates_result.timestamp,
        )

    def _get_rate_payload(self) -> tuple[dict[str, Any], bool, str]:
        """Return ``(api_payload, cached, source)`` from cache or a new API request."""
        ensure_data_directories()
        cached = self._load_cache()
        if cached and self._is_cache_valid(cached):
            payload = cached.get("data")
            if isinstance(payload, dict):
                logger.info("Using cached exchange rates from %s", self.cache_file)
                return payload, True, "cache"

        payload = self._fetch_from_api()
        self._save_cache(payload)
        return payload, False, "api"

    def _fetch_from_api(self) -> dict[str, Any]:
        """Request latest rates from the external API with retry and rate limiting."""
        self._apply_rate_limit()
        logger.info("Fetching exchange rates from %s", self.api_url)

        last_error: Exception | None = None
        for attempt in range(MAX_RETRIES):
            try:
                response = requests.get(self.api_url, timeout=REQUEST_TIMEOUT_SECONDS)
                self._handle_http_errors(response)
                return self._parse_json_response(response)
            except requests.Timeout as exc:
                last_error = ExchangeTimeoutError("Exchange API request timed out")
                last_error.__cause__ = exc
            except requests.ConnectionError as exc:
                last_error = ExchangeNetworkError(f"Network error: {exc}")
            except ExchangeAPIError:
                raise
            except ExchangeInvalidResponseError:
                raise
            except requests.RequestException as exc:
                last_error = ExchangeNetworkError(f"Network error: {exc}")

            if attempt < MAX_RETRIES - 1:
                delay = BACKOFF_BASE_SECONDS * (2**attempt)
                logger.warning(
                    "Exchange API attempt %s failed; retrying in %ss",
                    attempt + 1,
                    delay,
                )
                time.sleep(delay)

        raise last_error or ExchangeNetworkError("Failed to fetch exchange rates")

    def _parse_json_response(self, response: requests.Response) -> dict[str, Any]:
        """Parse and validate JSON body from the API."""
        try:
            payload = response.json()
        except ValueError as exc:
            raise ExchangeInvalidResponseError("Invalid JSON in API response") from exc

        if not isinstance(payload, dict) or "rates" not in payload:
            raise ExchangeInvalidResponseError("API response missing 'rates'")

        rates = payload.get("rates")
        if not isinstance(rates, dict):
            raise ExchangeInvalidResponseError("API 'rates' must be an object")

        return payload

    def _handle_http_errors(self, response: requests.Response) -> None:
        """Map HTTP status codes to domain exceptions."""
        if response.status_code == 429:
            raise ExchangeAPIError("API rate limit exceeded")
        if response.status_code >= 400:
            raise ExchangeAPIError(
                f"API error {response.status_code}: {response.text[:200]}"
            )

    def _apply_rate_limit(self) -> None:
        """Sleep briefly before an external API call."""
        time.sleep(self.request_delay)

    def _load_cache(self) -> dict[str, Any] | None:
        """Read cache file if it exists."""
        if not self.cache_file.is_file():
            return None
        try:
            with self.cache_file.open(encoding="utf-8") as handle:
                data = json.load(handle)
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Ignoring invalid cache file: %s", exc)
            return None
        return data if isinstance(data, dict) else None

    def _save_cache(self, payload: dict[str, Any]) -> None:
        """Persist API payload with fetch timestamp."""
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_body = {
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "base": payload.get("base", self.base_currency),
            "data": payload,
        }
        with self.cache_file.open("w", encoding="utf-8") as handle:
            json.dump(cache_body, handle, indent=2)
        logger.info("Saved exchange rate cache to %s", self.cache_file)

    def _is_cache_valid(self, cached: dict[str, Any]) -> bool:
        """True when ``fetched_at`` is present and younger than ``cache_ttl_seconds``."""
        fetched_at = cached.get("fetched_at")
        if not fetched_at:
            return False
        try:
            fetched_time = datetime.fromisoformat(str(fetched_at))
        except ValueError:
            return False
        if fetched_time.tzinfo is None:
            fetched_time = fetched_time.replace(tzinfo=timezone.utc)
        age_seconds = (datetime.now(timezone.utc) - fetched_time).total_seconds()
        return age_seconds < self.cache_ttl_seconds

    def _build_rates_result(
        self,
        payload: dict[str, Any],
        currencies: tuple[str, ...],
        cached: bool,
        source: str,
    ) -> ExchangeRatesResult:
        """Build result with BGN-per-unit rates for requested currencies."""
        api_rates = payload.get("rates", {})
        if not isinstance(api_rates, dict):
            raise ExchangeInvalidResponseError("Cached payload missing rates")

        rates_per_bgn: dict[str, float] = {self.base_currency: 1.0}
        bgn_per_unit: dict[str, float] = {self.base_currency: 1.0}

        for code in currencies:
            self._validate_currency(code)
            if code == self.base_currency:
                continue
            if code not in api_rates:
                raise ExchangeCurrencyNotFoundError(f"Currency not found: {code}")
            per_bgn = float(api_rates[code])
            if per_bgn <= 0:
                raise ExchangeInvalidResponseError(f"Invalid rate for {code}")
            rates_per_bgn[code] = per_bgn
            bgn_per_unit[code] = 1.0 / per_bgn

        timestamp = self._resolve_timestamp(cached)
        return ExchangeRatesResult(
            base=self.base_currency,
            rates_per_bgn=rates_per_bgn,
            bgn_per_unit=bgn_per_unit,
            timestamp=timestamp,
            cached=cached,
            source=source,
        )

    def _resolve_timestamp(self, cached: bool) -> str:
        """Use cache ``fetched_at`` when served from cache, otherwise current UTC time."""
        cached_file = self._load_cache()
        if cached and cached_file and cached_file.get("fetched_at"):
            return str(cached_file["fetched_at"])
        return datetime.now(timezone.utc).isoformat()

    def _normalize_currencies(self, currencies: tuple[str, ...]) -> tuple[str, ...]:
        """Uppercase currency codes for consistent lookups."""
        return tuple(currency.upper() for currency in currencies)

    def _validate_currency(self, code: str) -> None:
        """Raise ``ExchangeCurrencyNotFoundError`` for unsupported codes."""
        if code not in SUPPORTED_CURRENCIES:
            raise ExchangeCurrencyNotFoundError(f"Unsupported currency: {code}")

    @staticmethod
    def _convert_amount(
        amount: float,
        from_currency: str,
        to_currency: str,
        rates_per_bgn: dict[str, float],
    ) -> tuple[float, float]:
        """Convert using API rates where ``rates_per_bgn[X]`` is X per 1 BGN."""
        if from_currency == to_currency:
            return amount, 1.0

        if from_currency == "BGN":
            rate = rates_per_bgn[to_currency]
            return amount * rate, rate

        if to_currency == "BGN":
            rate = 1.0 / rates_per_bgn[from_currency]
            return amount / rates_per_bgn[from_currency], rate

        via_bgn = amount / rates_per_bgn[from_currency]
        converted = via_bgn * rates_per_bgn[to_currency]
        rate = rates_per_bgn[to_currency] / rates_per_bgn[from_currency]
        return converted, rate
