"""Exchange rate history repository tests."""

from datetime import date, datetime, timedelta, timezone

from app.models.exchange_rate import ExchangeRateRecord
from app.repositories.exchange_rate_repository import ExchangeRateRepository


def _row(
    target: str,
    rate: float,
    rate_date: date,
    *,
    collected_at: datetime | None = None,
) -> dict:
    return {
        "base_currency": "BGN",
        "target_currency": target,
        "rate": rate,
        "rate_date": rate_date,
        "collected_at": collected_at or datetime(2024, 6, 2, 12, 0, tzinfo=timezone.utc),
        "source": "test",
    }


def test_save_rates_inserts_rows(db_session):
    repo = ExchangeRateRepository(db_session)
    inserted, updated = repo.save_rates(
        [
            _row("EUR", 1.95, date(2024, 6, 1)),
            _row("USD", 1.80, date(2024, 6, 1)),
        ]
    )
    db_session.commit()

    assert inserted == 2
    assert updated == 0
    latest = repo.get_latest_rates("BGN")
    assert len(latest) == 2
    assert {r.target_currency for r in latest} == {"EUR", "USD"}


def test_save_rates_upserts_same_currency_date(db_session):
    repo = ExchangeRateRepository(db_session)
    repo.save_rates([_row("EUR", 1.95, date(2024, 6, 1))])
    inserted, updated = repo.save_rates([_row("EUR", 1.97, date(2024, 6, 1))])
    db_session.commit()

    assert inserted == 0
    assert updated == 1
    latest = repo.get_latest_rates("BGN")
    assert len(latest) == 1
    assert latest[0].rate == 1.97


def test_get_history_filters_by_days(db_session):
    today = datetime.now(timezone.utc).date()
    repo = ExchangeRateRepository(db_session)
    repo.save_rates(
        [
            _row("EUR", 1.90, today - timedelta(days=5)),
            _row("EUR", 1.95, today - timedelta(days=1)),
            _row("EUR", 1.97, today),
        ]
    )
    db_session.commit()

    history = repo.get_history("BGN", days=3)
    dates = {r.rate_date for r in history}
    assert today - timedelta(days=5) not in dates
    assert today - timedelta(days=1) in dates
    assert today in dates


def test_get_previous_rate_returns_prior_day(db_session):
    repo = ExchangeRateRepository(db_session)
    repo.save_rates(
        [
            _row("EUR", 1.90, date(2024, 6, 1)),
            _row("EUR", 1.95, date(2024, 6, 2)),
        ]
    )
    db_session.commit()

    previous = repo.get_previous_rate("BGN", "EUR", date(2024, 6, 2))
    assert previous is not None
    assert previous.rate == 1.90
    assert previous.rate_date == date(2024, 6, 1)


def test_get_previous_rate_none_when_missing(db_session):
    repo = ExchangeRateRepository(db_session)
    repo.save_rates([_row("EUR", 1.95, date(2024, 6, 2))])
    db_session.commit()

    assert repo.get_previous_rate("BGN", "EUR", date(2024, 6, 2)) is None


def test_upsert_rate_returns_inserted_flag(db_session):
    repo = ExchangeRateRepository(db_session)
    collected = datetime(2024, 6, 1, tzinfo=timezone.utc)
    _, inserted = repo.upsert_rate(
        base_currency="BGN",
        target_currency="GBP",
        rate=2.30,
        rate_date=date(2024, 6, 1),
        collected_at=collected,
        source="test",
    )
    _, updated = repo.upsert_rate(
        base_currency="BGN",
        target_currency="GBP",
        rate=2.31,
        rate_date=date(2024, 6, 1),
        collected_at=collected,
        source="test",
    )
    db_session.commit()

    assert inserted is True
    assert updated is False
    row = db_session.query(ExchangeRateRecord).one()
    assert row.rate == 2.31
