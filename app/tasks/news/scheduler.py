"""Background scheduler for periodic RSS news refresh (Task 5)."""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING

from app.core.database import session_scope
from app.core.logging_config import get_logger
from app.services.news_service import NewsApplicationService

if TYPE_CHECKING:
    from app.core.config import Settings

logger = get_logger(__name__)


class NewsRefreshScheduler:
    """Runs ``NewsApplicationService.refresh`` on a fixed interval in a daemon thread."""

    def __init__(self, settings: Settings | None = None) -> None:
        if settings is None:
            from app.core.config import get_settings

            settings = get_settings()
        self._settings = settings
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        """Start the background scheduler when enabled in settings."""
        if not self._settings.news_scheduler_enabled:
            return
        if self.is_running:
            return

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run_loop,
            name="news-refresh-scheduler",
            daemon=True,
        )
        self._thread.start()
        logger.info(
            "News scheduler started: interval_minutes=%d",
            self._settings.news_scheduler_interval_minutes,
        )

    def stop(self) -> None:
        """Signal the scheduler thread to stop and wait briefly for exit."""
        if self._thread is None:
            return

        self._stop_event.set()
        self._thread.join(timeout=5.0)
        self._thread = None
        logger.info("News scheduler stopped")

    def _run_loop(self) -> None:
        interval_seconds = self._settings.news_scheduler_interval_minutes * 60
        while not self._stop_event.is_set():
            if self._stop_event.wait(timeout=interval_seconds):
                break
            self.run_scheduled_refresh()

    def run_scheduled_refresh(self) -> None:
        """Execute one refresh cycle; errors are logged and not re-raised."""
        logger.info("News scheduler refresh started")
        try:
            with session_scope() as session:
                service = NewsApplicationService(session)
                result = service.refresh()
            if result.errors:
                logger.warning(
                    "News scheduler refresh completed with feed errors: %s",
                    result.errors,
                )
            logger.info(
                "News scheduler refresh completed: inserted=%d skipped_duplicates=%d errors=%d",
                result.inserted_count,
                result.skipped_duplicates,
                len(result.errors),
            )
        except Exception:
            logger.exception("News scheduler refresh failed")
