"""Rates history application service tests."""

from datetime import date, datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.repositories.exchange_rate_repository import ExchangeRateRepository
from app.services.rates_history_service import RatesHistoryApplicationService
from app.tasks.exchange.exceptions import ExchangeError
from app.tasks.exchange.models import ExchangeRatesResult


def _live_result(*, timestamp: str = "2024-06-02T10:00:00Z") -> ExchangeRatesResult:
    return ExchangeRatesResult(
        base="BGN",
        rates_per_bgn={"BGN": 1.0, "EUR": 0.511, "USD": 0.593, "GBP": 0.442},
        bgn_per_unit={"EUR": 1.957, "USD": 1.686, "GBP": 2.262},
        timestamp=timestamp,
        cached=False,
        source="exchangerate-api",
    )


def test_refresh_saves_rates_and_metadata(db_session):
    service = RatesHistoryApplicationService(db_session)

    with patch.object(service._exchange, "get_rates", return_value=_live_result()):
        result = service.refresh()

    assert result.inserted_count == 3
    assert result.updated_count == 0
    assert result.source == "exchangerate-api"
    assert not result.errors

    metadata = service.get_refresh_metadata()
    assert metadata["last_refresh_at"] is not None
    assert metadata["source"] == "exchangerate-api"
    assert metadata["last_inserted_count"] == 3


def test_refresh_handles_exchange_error(db_session):
    service = RatesHistoryApplicationService(db_session)

    with patch.object(
        service._exchange,
        "get_rates",
        side_effect=ExchangeError("API unavailable"),
    ):
        result = service.refresh()

    assert result.inserted_count == 0
    assert len(result.errors) == 1
    assert result.errors[0]["source"] == "exchange_api"


def test_daily_change_calculation(db_session):
    repo = ExchangeRateRepository(db_session)
    repo.save_rates(
        [
            {
                "base_currency": "BGN",
                "target_currency": "EUR",
                "rate": 1.90,
                "rate_date": date(2024, 6, 1),
                "collected_at": datetime(2024, 6, 1, tzinfo=timezone.utc),
                "source": "test",
            },
            {
                "base_currency": "BGN",
                "target_currency": "EUR",
                "rate": 1.95,
                "rate_date": date(2024, 6, 2),
                "collected_at": datetime(2024, 6, 2, tzinfo=timezone.utc),
                "source": "test",
            },
        ]
    )
    db_session.commit()

    service = RatesHistoryApplicationService(db_session)
    data = service.get_latest_with_changes()
    eur = next(r for r in data["rates"] if r["target_currency"] == "EUR")

    assert eur["daily_change"] == pytest.approx(0.05)
    assert eur["daily_change_pct"] == pytest.approx((0.05 / 1.90) * 100, rel=1e-3)


def test_daily_change_null_without_previous(db_session):
    repo = ExchangeRateRepository(db_session)
    repo.save_rates(
        [
            {
                "base_currency": "BGN",
                "target_currency": "USD",
                "rate": 1.80,
                "rate_date": date(2024, 6, 5),
                "collected_at": datetime(2024, 6, 5, tzinfo=timezone.utc),
                "source": "test",
            },
        ]
    )
    db_session.commit()

    service = RatesHistoryApplicationService(db_session)
    usd = service.get_latest_with_changes()["rates"][0]

    assert usd["daily_change"] is None
    assert usd["daily_change_pct"] is None


def test_refresh_rejects_invalid_rates(db_session):
    bad = _live_result()
    bad.bgn_per_unit = {"EUR": -1.0, "USD": 1.686, "GBP": 2.262}
    service = RatesHistoryApplicationService(db_session)

    with patch.object(service._exchange, "get_rates", return_value=bad):
        result = service.refresh()

    assert result.inserted_count == 2
    assert any(e["source"] == "EUR" for e in result.errors)
