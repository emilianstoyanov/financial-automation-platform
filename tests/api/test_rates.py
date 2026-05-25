"""Exchange rate history API endpoint tests."""

from datetime import date, datetime, timedelta, timezone
from unittest.mock import patch

from app.tasks.exchange.models import ExchangeRatesResult


def _live_result() -> ExchangeRatesResult:
    return ExchangeRatesResult(
        base="BGN",
        rates_per_bgn={"BGN": 1.0, "EUR": 0.511, "USD": 0.593, "GBP": 0.442},
        bgn_per_unit={"EUR": 1.957, "USD": 1.686, "GBP": 2.262},
        timestamp="2024-06-02T12:00:00+00:00",
        cached=False,
        source="exchangerate-api",
    )


def _seed_rate(db_session, target: str, rate: float, rate_date: date) -> None:
    from app.models.exchange_rate import ExchangeRateRecord

    db_session.add(
        ExchangeRateRecord(
            base_currency="BGN",
            target_currency=target,
            rate=rate,
            rate_date=rate_date,
            collected_at=datetime(2024, 6, 2, 10, 0, tzinfo=timezone.utc),
            source="seed",
        )
    )
    db_session.commit()


def test_get_rates_empty(client):
    response = client.get("/api/v1/rates")
    assert response.status_code == 200
    data = response.json()
    assert data["base_currency"] == "BGN"
    assert data["rates"] == []
    assert data["last_refresh_at"] is None


def test_get_rates_returns_stored_with_daily_change(client, db_session):
    _seed_rate(db_session, "EUR", 1.90, date(2024, 6, 1))
    _seed_rate(db_session, "EUR", 1.95, date(2024, 6, 2))

    response = client.get("/api/v1/rates")
    assert response.status_code == 200
    data = response.json()
    assert len(data["rates"]) == 1
    eur = data["rates"][0]
    assert eur["target_currency"] == "EUR"
    assert eur["rate"] == 1.95
    assert eur["daily_change"] == 0.05
    assert eur["daily_change_pct"] is not None


def test_get_rates_history(client, db_session):
    today = datetime.now(timezone.utc).date()
    _seed_rate(db_session, "EUR", 1.90, today - timedelta(days=1))
    _seed_rate(db_session, "EUR", 1.95, today)
    _seed_rate(db_session, "USD", 1.80, today)

    response = client.get("/api/v1/rates/history?days=7")
    assert response.status_code == 200
    data = response.json()
    assert data["days"] == 7
    assert len(data["history"]) >= 2


def test_post_rates_refresh_mocked(client, db_session):
    with patch(
        "app.services.rates_history_service.ExchangeApplicationService.get_rates",
        return_value=_live_result(),
    ):
        response = client.post("/api/v1/rates/refresh")

    assert response.status_code == 200
    data = response.json()
    assert data["inserted_count"] == 3
    assert len(data["rates"]) == 3
    assert data["source"] == "exchangerate-api"

    get_resp = client.get("/api/v1/rates")
    assert len(get_resp.json()["rates"]) == 3
