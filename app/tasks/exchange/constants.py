"""Exchange rate client constants."""

from typing import Final
from app.core.data_dirs import EXCHANGE_DATA_DIR

DEFAULT_BASE_CURRENCY: Final[str] = "BGN"
DEFAULT_CACHE_FILE: Final[str] = str(EXCHANGE_DATA_DIR / "cache.json")

TARGET_CURRENCIES: Final[tuple[str, ...]] = ("EUR", "USD", "GBP")
SUPPORTED_CURRENCIES: Final[frozenset[str]] = frozenset(
    {DEFAULT_BASE_CURRENCY, *TARGET_CURRENCIES}
)

CACHE_TTL_SECONDS: Final[int] = 3600
MAX_RETRIES: Final[int] = 3
REQUEST_DELAY_SECONDS: Final[float] = 0.5
REQUEST_TIMEOUT_SECONDS: Final[int] = 10
BACKOFF_BASE_SECONDS: Final[float] = 1.0
