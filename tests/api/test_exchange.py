"""Exchange rate API endpoint tests."""

from datetime import datetime, timezone
from unittest.mock import patch

from app.tasks.exchange.models import ConversionResult, ExchangeRatesResult


def test_get_exchange_rates_endpoint(client):
    """GET /exchange/rates returns BGN-based rates with cache metadata."""
    mock_result = ExchangeRatesResult(
        base="BGN",
        rates_per_bgn={"BGN": 1.0, "EUR": 0.511, "USD": 0.593, "GBP": 0.442},
        bgn_per_unit={"BGN": 1.0, "EUR": 1.957, "USD": 1.686, "GBP": 2.262},
        timestamp=datetime.now(timezone.utc).isoformat(),
        cached=True,
        source="cache",
    )

    with patch(
        "app.api.v1.exchange.ExchangeApplicationService.get_rates",
        return_value=mock_result,
    ):
        response = client.get("/api/v1/exchange/rates")

    assert response.status_code == 200
    data = response.json()
    assert data["base"] == "BGN"
    assert "EUR" in data["rates"]
    assert data["cached"] is True


def test_convert_endpoint(client):
    """GET /exchange/convert returns conversion fields for EUR to BGN."""
    mock_result = ConversionResult(
        from_currency="EUR",
        to_currency="BGN",
        original_amount=100.0,
        converted_amount=195.69,
        rate=1.9569,
        source="cache",
        cached=True,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )

    with patch(
        "app.api.v1.exchange.ExchangeApplicationService.convert",
        return_value=mock_result,
    ):
        response = client.get(
            "/api/v1/exchange/convert",
            params={"from_currency": "EUR", "to_currency": "BGN", "amount": 100},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["from_currency"] == "EUR"
    assert data["converted_amount"] == 195.69
    assert data["cached"] is True
