"""Unit tests for exchange rate client."""

import json
import pytest
import requests
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta, timezone
from app.tasks.exchange.client import ExchangeRateClient
from app.tasks.exchange.constants import TARGET_CURRENCIES
from app.tasks.exchange.exceptions import (
    ExchangeAPIError,
    ExchangeCurrencyNotFoundError,
    ExchangeInvalidResponseError,
    ExchangeTimeoutError,
)

MOCK_API_PAYLOAD = {
    "base": "BGN",
    "date": "2026-05-23",
    "rates": {"BGN": 1, "EUR": 0.511, "USD": 0.593, "GBP": 0.442},
}


def _mock_response(status_code: int = 200, json_data: dict | None = None, text: str = ""):
    response = MagicMock()
    response.status_code = status_code
    response.text = text
    response.json.return_value = json_data or MOCK_API_PAYLOAD
    return response


def _write_cache(path, fetched_at: datetime, payload: dict | None = None) -> None:
    path.write_text(
        json.dumps(
            {
                "fetched_at": fetched_at.isoformat(),
                "base": "BGN",
                "data": payload or MOCK_API_PAYLOAD,
            }
        ),
        encoding="utf-8",
    )


def test_cache_validation_accepts_fresh_entry(tmp_path):
    """Fresh cache within TTL is considered valid."""
    client = ExchangeRateClient(cache_file=tmp_path / "cache.json")
    cached = {"fetched_at": datetime.now(timezone.utc).isoformat(), "data": MOCK_API_PAYLOAD}
    assert client._is_cache_valid(cached) is True


def test_cache_validation_rejects_stale_or_invalid(tmp_path):
    """Stale or malformed cache entries are rejected."""
    client = ExchangeRateClient(cache_file=tmp_path / "cache.json", cache_ttl_seconds=3600)
    stale = {
        "fetched_at": (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat(),
        "data": MOCK_API_PAYLOAD,
    }
    assert client._is_cache_valid(stale) is False
    assert client._is_cache_valid({}) is False
    assert client._is_cache_valid({"fetched_at": "not-a-date"}) is False


def test_cache_usage_when_valid(tmp_path):
    """Fresh cache is served without calling the external API."""
    cache_file = tmp_path / "cache.json"
    _write_cache(cache_file, datetime.now(timezone.utc))

    client = ExchangeRateClient(cache_file=cache_file, request_delay=0)
    with patch("app.tasks.exchange.client.requests.get") as mock_get:
        result = client.get_rates()

    mock_get.assert_not_called()
    assert result.cached is True
    assert result.source == "cache"


def test_api_fetch_when_cache_expired(tmp_path):
    """Expired cache triggers a live API fetch and marks source as api."""
    cache_file = tmp_path / "cache.json"
    _write_cache(cache_file, datetime.now(timezone.utc) - timedelta(hours=2))

    client = ExchangeRateClient(cache_file=cache_file, request_delay=0)
    with patch("app.tasks.exchange.client.requests.get", return_value=_mock_response()) as mock_get:
        result = client.get_rates()

    mock_get.assert_called_once()
    assert result.cached is False
    assert result.source == "api"


def test_retry_on_timeout_then_succeeds(tmp_path):
    """A timeout on the first attempt is retried and then succeeds."""
    client = ExchangeRateClient(cache_file=tmp_path / "cache.json", request_delay=0)
    with patch("app.tasks.exchange.client.time.sleep"), patch(
            "app.tasks.exchange.client.requests.get",
            side_effect=[requests.Timeout(), _mock_response()],
    ) as mock_get:
        result = client.get_rates()

    assert mock_get.call_count == 2
    assert result.source == "api"


def test_raises_after_max_retries(tmp_path):
    """Repeated timeouts raise ExchangeTimeoutError after three attempts."""
    client = ExchangeRateClient(cache_file=tmp_path / "cache.json", request_delay=0)
    with patch("app.tasks.exchange.client.time.sleep"), patch(
            "app.tasks.exchange.client.requests.get",
            side_effect=requests.Timeout(),
    ):
        with pytest.raises(ExchangeTimeoutError):
            client.get_rates()


def test_invalid_json_raises(tmp_path):
    """Non-JSON API body raises ExchangeInvalidResponseError."""
    client = ExchangeRateClient(cache_file=tmp_path / "cache.json", request_delay=0)
    bad_response = _mock_response()
    bad_response.json.side_effect = ValueError("bad json")
    with patch("app.tasks.exchange.client.requests.get", return_value=bad_response):
        with pytest.raises(ExchangeInvalidResponseError):
            client.get_rates()


def test_api_rate_limit_raises(tmp_path):
    """HTTP 429 from the API raises ExchangeAPIError."""
    client = ExchangeRateClient(cache_file=tmp_path / "cache.json", request_delay=0)
    with patch("app.tasks.exchange.client.requests.get", return_value=_mock_response(status_code=429)):
        with pytest.raises(ExchangeAPIError, match="rate limit"):
            client.get_rates()


def test_http_404_raises_exchange_api_error(tmp_path):
    """HTTP 404 raises ExchangeAPIError without retrying."""
    client = ExchangeRateClient(cache_file=tmp_path / "cache.json", request_delay=0)
    with patch(
            "app.tasks.exchange.client.requests.get",
            return_value=_mock_response(status_code=404, text="Not Found"),
    ) as mock_get:
        with pytest.raises(ExchangeAPIError, match="404"):
            client.get_rates()

    mock_get.assert_called_once()


def test_http_500_raises_exchange_api_error_without_retry(tmp_path):
    """HTTP 500 raises ExchangeAPIError and does not retry."""
    client = ExchangeRateClient(cache_file=tmp_path / "cache.json", request_delay=0)
    with patch(
            "app.tasks.exchange.client.requests.get",
            return_value=_mock_response(status_code=500, text="Internal Server Error"),
    ) as mock_get:
        with pytest.raises(ExchangeAPIError, match="500"):
            client.get_rates()

    mock_get.assert_called_once()


def test_rates_response_contains_eur_usd_gbp(tmp_path):
    """get_rates includes positive BGN-per-unit values for EUR, USD, and GBP."""
    cache_file = tmp_path / "cache.json"
    _write_cache(cache_file, datetime.now(timezone.utc))

    client = ExchangeRateClient(cache_file=cache_file, request_delay=0)
    result = client.get_rates()

    for code in TARGET_CURRENCIES:
        assert code in result.bgn_per_unit
        assert result.bgn_per_unit[code] > 0


def test_currency_conversion_eur_to_bgn(tmp_path):
    """100 EUR converts to BGN using the cached EUR rate from the API payload."""
    cache_file = tmp_path / "cache.json"
    _write_cache(cache_file, datetime.now(timezone.utc))

    client = ExchangeRateClient(cache_file=cache_file, request_delay=0)
    result = client.convert("EUR", "BGN", 100)

    assert result.converted_amount == pytest.approx(100 / 0.511, rel=1e-4)
    assert result.rate == pytest.approx(1 / 0.511, rel=1e-4)


def test_invalid_currency_raises(tmp_path):
    """Unsupported currencies such as JPY raise ExchangeCurrencyNotFoundError."""
    client = ExchangeRateClient(cache_file=tmp_path / "cache.json", request_delay=0)
    with pytest.raises(ExchangeCurrencyNotFoundError):
        client.convert("JPY", "BGN", 10)
