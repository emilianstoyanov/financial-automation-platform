"""Tests for RSS news background scheduler."""

from unittest.mock import MagicMock, patch

import pytest

from app.core.config import Settings
from app.tasks.news.models import RefreshCollectionResult
from app.tasks.news.scheduler import NewsRefreshScheduler


def _settings(*, enabled: bool = False, interval_minutes: int = 1440) -> Settings:
    return Settings(
        NEWS_SCHEDULER_ENABLED=enabled,
        NEWS_SCHEDULER_INTERVAL_MINUTES=interval_minutes,
    )


def test_scheduler_disabled_by_default():
    """Scheduler stays off when NEWS_SCHEDULER_ENABLED is false."""
    settings = _settings(enabled=False, interval_minutes=1440)
    assert settings.news_scheduler_enabled is False
    assert settings.news_scheduler_interval_minutes == 1440
    assert Settings.model_fields["news_scheduler_enabled"].default is False

    scheduler = NewsRefreshScheduler(settings)
    scheduler.start()

    assert scheduler.is_running is False


def test_scheduler_enabled_starts_background_thread():
    """When enabled, start() launches the daemon scheduler thread."""
    scheduler = NewsRefreshScheduler(_settings(enabled=True, interval_minutes=60))
    scheduler.start()

    try:
        assert scheduler.is_running is True
    finally:
        scheduler.stop()
        assert scheduler.is_running is False


def test_run_scheduled_refresh_calls_news_service():
    """Scheduled refresh delegates to NewsApplicationService.refresh."""
    mock_result = RefreshCollectionResult(inserted_count=2, skipped_duplicates=1)
    mock_service = MagicMock()
    mock_service.refresh.return_value = mock_result

    scheduler = NewsRefreshScheduler(_settings(enabled=True))

    with patch(
        "app.tasks.news.scheduler.NewsApplicationService",
        return_value=mock_service,
    ):
        with patch("app.tasks.news.scheduler.session_scope") as mock_scope:
            mock_scope.return_value.__enter__.return_value = MagicMock()
            scheduler.run_scheduled_refresh()

    mock_service.refresh.assert_called_once()


def test_scheduler_handles_refresh_errors_without_raising():
    """Exceptions during refresh are logged and do not propagate."""
    scheduler = NewsRefreshScheduler(_settings(enabled=True))

    with patch(
        "app.tasks.news.scheduler.NewsApplicationService",
    ) as mock_cls:
        mock_cls.return_value.refresh.side_effect = RuntimeError("database unavailable")
        with patch("app.tasks.news.scheduler.session_scope") as mock_scope:
            mock_scope.return_value.__enter__.return_value = MagicMock()
            scheduler.run_scheduled_refresh()


def test_scheduler_loop_runs_refresh_when_stop_not_set():
    """Loop invokes refresh after the wait interval elapses."""
    scheduler = NewsRefreshScheduler(_settings(enabled=True, interval_minutes=1))

    with patch.object(scheduler, "run_scheduled_refresh") as mock_refresh:
        with patch.object(scheduler._stop_event, "wait", return_value=False) as mock_wait:
            with patch.object(scheduler._stop_event, "is_set", side_effect=[False, True]):
                scheduler._run_loop()

    mock_wait.assert_called_once()
    mock_refresh.assert_called_once()
