"""Tests for exchange rate history background scheduler."""

from unittest.mock import MagicMock, patch

from app.core.config import Settings
from app.services.rates_history_service import RatesRefreshResult
from app.tasks.exchange.scheduler import RatesRefreshScheduler


def _settings(*, enabled: bool = False, interval_minutes: int = 1440) -> Settings:
    return Settings(
        RATES_SCHEDULER_ENABLED=enabled,
        RATES_SCHEDULER_INTERVAL_MINUTES=interval_minutes,
    )


def test_rates_scheduler_disabled_by_default():
    settings = _settings(enabled=False)
    scheduler = RatesRefreshScheduler(settings)
    scheduler.start()
    assert scheduler.is_running is False


def test_rates_scheduler_enabled_starts_thread():
    scheduler = RatesRefreshScheduler(_settings(enabled=True, interval_minutes=60))
    scheduler.start()
    try:
        assert scheduler.is_running is True
    finally:
        scheduler.stop()
        assert scheduler.is_running is False


def test_run_scheduled_refresh_calls_rates_service():
    mock_result = RatesRefreshResult(inserted_count=3, source="test")
    mock_service = MagicMock()
    mock_service.refresh.return_value = mock_result

    scheduler = RatesRefreshScheduler(_settings(enabled=True))

    with patch(
        "app.tasks.exchange.scheduler.RatesHistoryApplicationService",
        return_value=mock_service,
    ):
        with patch("app.tasks.exchange.scheduler.session_scope") as mock_scope:
            mock_scope.return_value.__enter__.return_value = MagicMock()
            scheduler.run_scheduled_refresh()

    mock_service.refresh.assert_called_once()


def test_rates_scheduler_handles_errors_without_raising():
    scheduler = RatesRefreshScheduler(_settings(enabled=True))

    with patch(
        "app.tasks.exchange.scheduler.RatesHistoryApplicationService",
    ) as mock_cls:
        mock_cls.return_value.refresh.side_effect = RuntimeError("database unavailable")
        with patch("app.tasks.exchange.scheduler.session_scope") as mock_scope:
            mock_scope.return_value.__enter__.return_value = MagicMock()
            scheduler.run_scheduled_refresh()


def test_rates_scheduler_loop_invokes_refresh():
    scheduler = RatesRefreshScheduler(_settings(enabled=True, interval_minutes=1))

    with patch.object(scheduler, "run_scheduled_refresh") as mock_refresh:
        with patch.object(scheduler._stop_event, "wait", return_value=False):
            with patch.object(scheduler._stop_event, "is_set", side_effect=[False, True]):
                scheduler._run_loop()

    mock_refresh.assert_called_once()
