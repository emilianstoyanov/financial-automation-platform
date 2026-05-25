"""Background scheduler for periodic exchange rate history refresh (Task 5)."""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING

from app.core.database import session_scope
from app.core.logging_config import get_logger
from app.services.rates_history_service import RatesHistoryApplicationService

if TYPE_CHECKING:
    from app.core.config import Settings

logger = get_logger(__name__)


class RatesRefreshScheduler:
    """Runs ``RatesHistoryApplicationService.refresh`` on a fixed interval."""

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
        if not self._settings.rates_scheduler_enabled:
            return
        if self.is_running:
            return

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run_loop,
            name="rates-refresh-scheduler",
            daemon=True,
        )
        self._thread.start()
        logger.info(
            "Rates scheduler started: interval_minutes=%d",
            self._settings.rates_scheduler_interval_minutes,
        )

    def stop(self) -> None:
        if self._thread is None:
            return
        self._stop_event.set()
        self._thread.join(timeout=5.0)
        self._thread = None
        logger.info("Rates scheduler stopped")

    def _run_loop(self) -> None:
        interval_seconds = self._settings.rates_scheduler_interval_minutes * 60
        while not self._stop_event.is_set():
            if self._stop_event.wait(timeout=interval_seconds):
                break
            self.run_scheduled_refresh()

    def run_scheduled_refresh(self) -> None:
        logger.info("Rates scheduler refresh started")
        try:
            with session_scope() as session:
                service = RatesHistoryApplicationService(session)
                result = service.refresh()
            if result.errors:
                logger.warning(
                    "Rates scheduler refresh completed with errors: %s",
                    result.errors,
                )
            logger.info(
                "Rates scheduler refresh completed: inserted=%d updated=%d errors=%d",
                result.inserted_count,
                result.updated_count,
                len(result.errors),
            )
        except Exception:
            logger.exception("Rates scheduler refresh failed")
